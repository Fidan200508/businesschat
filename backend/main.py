import os
import joblib
import shap
import numpy as np
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import timedelta
import json
import asyncio
from fastapi import Request
from fastapi.responses import JSONResponse
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
except ModuleNotFoundError:
    Limiter = None
    RateLimitExceeded = None

    def get_remote_address(request: Request):
        return request.client.host if request.client else "local"

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(dotenv_path=None, *args, **kwargs):
        path = dotenv_path or os.path.join(os.getcwd(), ".env")
        if not os.path.exists(path):
            return False
        with open(path, encoding="utf-8") as env_file:
            for line in env_file:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        return True
# encryption imported where needed; encrypt_value not currently used in routes

load_dotenv()

from . import models, database, auth, agents
from .agents import advisor_graph
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Corporate Loan Risk API")

# Rate limiter setup
if Limiter is not None:
    limiter = Limiter(key_func=get_remote_address)
else:
    class _NoOpLimiter:
        def limit(self, _limit: str):
            def decorator(func):
                return func
            return decorator

    limiter = _NoOpLimiter()

app.state.limiter = limiter

if RateLimitExceeded is not None:
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"error": "Too many requests. Please wait and try again."}
        )

# CORS — restricted to frontend only
_allowed_origins = ["http://localhost:3000", "http://localhost:5173"]
_production_origin = os.getenv("FRONTEND_ORIGIN")
if _production_origin:
    _allowed_origins.append(_production_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/")
def health_check():
    return {"status": "ok"}

# Load the ML Model
try:
    # Ensure it looks in the correct path relative to the backend
    base_dir = os.path.dirname(os.path.dirname(__file__))
    model_path = os.path.join(base_dir, "extra_trees_model.pkl")
    model = joblib.load(model_path)
    explainer = shap.TreeExplainer(model)
except Exception as e:
    print(f"Failed to load model: {e}")
    model = None
    explainer = None

# Pydantic Schemas
class UserCreate(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class PredictionRequest(BaseModel):
    total_assets: float
    total_liabilities: float
    current_assets: float
    current_liabilities: float
    net_income: float
    revenue: float
    operating_income: float
    cash_flow: float
    credit_score: float
    
class ExplanationItem(BaseModel):
    feature: str
    importance: float
    impact: str

class PredictionResponse(BaseModel):
    risk_label: int
    debt_equity_ratio: float
    message: str
    explanations: List[ExplanationItem] = []

class HistoryResponse(BaseModel):
    id: int
    total_assets: float
    total_liabilities: float
    debt_equity_ratio: float
    credit_score: float
    risk_label: int
    created_at: str
    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    reply: str

# --- Authentication Routes ---
@app.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/token", response_model=Token)
@limiter.limit("5/minute")
def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- Prediction Routes ---
@app.post("/predict", response_model=PredictionResponse)
def predict_risk(req: PredictionRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    if model is None:
        raise HTTPException(status_code=500, detail="Model is not loaded on the server.")
        
    equity = req.total_assets - req.total_liabilities
    debt_equity_ratio = req.total_liabilities / equity if equity > 0 else 999.0

    feature_data = [
        req.total_assets,
        req.total_liabilities,
        req.current_assets,
        req.current_liabilities,
        req.net_income,
        req.revenue,
        req.operating_income,
        req.cash_flow,
        debt_equity_ratio
    ]
    
    prediction = model.predict([feature_data])[0]
    
    explanations = []
    if explainer is not None:
        try:
            feature_names = [
                "Total Assets", "Total Liabilities", "Current Assets", "Current Liabilities",
                "Net Income", "Revenue", "Operating Income", "Cash Flow", "Debt to Equity"
            ]
            shap_vals = explainer.shap_values(np.array([feature_data]))
            
            if isinstance(shap_vals, list) and len(shap_vals) == 2:
                class1_vals = shap_vals[1][0]
            elif isinstance(shap_vals, np.ndarray) and len(shap_vals.shape) == 3:
                class1_vals = shap_vals[0, :, 1]
            else:
                class1_vals = shap_vals[0]
                
            feat_imp = list(zip(feature_names, class1_vals))
            feat_imp.sort(key=lambda x: abs(x[1]), reverse=True)
            
            for f_name, f_val in feat_imp[:3]:
                imp_str = "increases risk" if f_val > 0 else "decreases risk"
                explanations.append({
                    "feature": f_name,
                    "importance": float(abs(f_val)),
                    "impact": imp_str
                })
        except Exception as e:
            print(f"SHAP explanation failed: {e}")
    
    # Save to history
    history_entry = models.PredictionHistory(
        user_id=current_user.id,
        total_assets=req.total_assets,
        total_liabilities=req.total_liabilities,
        current_assets=req.current_assets,
        current_liabilities=req.current_liabilities,
        net_income=req.net_income,
        revenue=req.revenue,
        operating_income=req.operating_income,
        cash_flow=req.cash_flow,
        debt_equity_ratio=debt_equity_ratio,
        credit_score=req.credit_score,
        risk_label=int(prediction)
    )
    db.add(history_entry)
    db.commit()

    message = "APPROVED" if prediction == 0 else "REJECTED"

    return PredictionResponse(
        risk_label=int(prediction),
        debt_equity_ratio=debt_equity_ratio,
        message=message,
        explanations=explanations
    )

@app.get("/history")
def get_history(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    records = db.query(models.PredictionHistory).filter(models.PredictionHistory.user_id == current_user.id).order_by(models.PredictionHistory.created_at.desc()).all()
    
    # Format the response manually to handle datetime serialization
    return [
        {
            "id": r.id,
            "total_assets": r.total_assets,
            "total_liabilities": r.total_liabilities,
            "debt_equity_ratio": r.debt_equity_ratio,
            "credit_score": r.credit_score,
            "risk_label": r.risk_label,
            "created_at": r.created_at.isoformat()
        } for r in records
    ]

@app.post("/chat", response_model=ChatResponse)
def chat_with_advisor(req: ChatRequest, current_user: models.User = Depends(auth.get_current_user)):
    msg = req.message.lower()
    ctx = req.context or {}
    
    # Financial Advisor Persona Logic
    reply = "I'm your AI Financial Advisor. How can I help you today?"
    
    # Split message into words for better matching
    words = msg.split()
    
    if "hello" in words or "hi" in words or "hey" in words:
        reply = f"Hello {current_user.username}! I'm here to analyze your loan application and provide advice. Feel free to ask me about your recent decision."
    
    elif "why" in msg or "reason" in msg or "reject" in msg or "explain" in msg or "means" in msg:
        if ctx.get("explanations"):
            reasons = []
            for exp in ctx['explanations']:
                impact_type = "Negative" if "increases" in exp['impact'] else "Positive"
                reasons.append(f"- **{exp['feature']}**: {exp['impact']} ({impact_type} impact)")
            
            reply = "Here is a breakdown of your analysis:\n\n" + "\n".join(reasons) + "\n\n"
            
            if "means" in msg or "explain" in msg:
                reply += "### What this means in plain English:\n"
                if any("Debt to Equity" in r for r in reasons):
                    reply += "- **Debt to Equity**: This measures how much debt you use to run your business vs your own money. A high ratio is risky because it means you owe a lot.\n"
                if any("Total Assets" in r for r in reasons):
                    reply += "- **Total Assets**: These are things your company owns (Cash, Equipment, etc.). Usually, more assets are good, but if they are low relative to debt, it's a concern.\n"
                if any("Net Income" in r for r in reasons):
                    reply += "- **Net Income**: This is your profit after all expenses. If this is low or negative, it shows the business might struggle to pay back a loan.\n"
            
            if ctx.get("risk_label") == 1:
                reply += "\n**Summary**: Your application was flagged as **High Risk** because your current financial ratios (especially those marked as 'increases risk') don't meet our safety thresholds."
            else:
                reply += "\n**Summary**: Your application was **Approved** because your strengths (especially those marked as 'decreases risk') outweigh your risk factors."
        else:
            reply = "I'd love to explain the results, but I don't see a recent analysis yet. Please fill out the form and click 'Analyze' first!"

    elif "improve" in msg or "better" in msg or "how" in msg:
        if ctx.get("explanations"):
            to_improve = [exp['feature'] for exp in ctx['explanations'] if "increases" in exp['impact']]
            if to_improve:
                reply = "To improve your approval chances for next time, I recommend:\n\n"
                for feat in to_improve:
                    if feat == "Debt to Equity":
                        reply += "1. **Lower your Debt**: Try to pay off existing liabilities or increase your company's equity capital.\n"
                    elif feat == "Net Income" or feat == "Operating Income":
                        reply += "2. **Boost Profitability**: Look for ways to reduce operational costs or increase sales margins.\n"
                    elif feat == "Credit Score":
                        reply += "3. **Credit Management**: Ensure all bills are paid on time to push your score above 720.\n"
                    else:
                        reply += f"4. **Optimize {feat}**: Try to move this metric closer to industry standards.\n"
            else:
                reply = "Your profile is excellent! Just keep doing what you're doing. Consistency is key to maintaining a low-risk profile."
        else:
            reply = "Generally, to get the best loan terms: 1. Keep your Debt-to-Equity below 2.0. 2. Maintain at least 6 months of cash flow in reserves. 3. Keep your Credit Score above 700."

    elif "business" in msg or "field" in msg:
        reply = "While our model analyzes individual financials, fields like **Technology, Healthcare, and Renewable Energy** are currently seeing very favorable risk ratings in the corporate sector due to their growth potential. High-overhead industries like traditional retail or heavy construction often face stricter scrutiny."

    elif "thank" in msg:
        reply = "You're very welcome! I'm glad I could help clarify things. Good luck with your business journey! 🚀"
    
    else:
        reply = "I'm specialized in explaining your loan risk analysis. You can ask me things like 'Why was I rejected?', 'What does Debt to Equity mean?', or 'How can I improve my chances?'"

    return ChatResponse(reply=reply)

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            req_data = json.loads(data)
            
            message = req_data.get("message", "")
            context = req_data.get("context", {})
            token = req_data.get("token", "")
            
            # Decode JWT directly — get_current_user() uses FastAPI Depends and
            # cannot be called as a plain function in a WebSocket handler.
            try:
                from jose import JWTError, jwt as jose_jwt
                payload = jose_jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
                username: str = payload.get("sub")
                if not username:
                    raise ValueError("No subject in token")
                user = db.query(models.User).filter(models.User.username == username).first()
                if user is None:
                    raise ValueError("User not found")
            except Exception:
                await websocket.send_json({"type": "error", "content": "Authentication failed"})
                continue

            # Initialize LangGraph State
            initial_state = {
                "messages": [{"role": "user", "content": message}],
                "context": context,
                "current_agent": "Supervisor",
                "final_reply": ""
            }

            # Run LangGraph and stream updates
            # advisor_graph.stream returns chunks as nodes are visited
            for output in advisor_graph.stream(initial_state):
                for key, value in output.items():
                    # value is the return of the node function
                    agent_name = value.get("current_agent", "Agent")
                    update_content = value.get("final_reply", "")
                    
                    # Send a "status update" to the UI
                    await websocket.send_json({
                        "type": "update",
                        "agent": agent_name,
                        "content": f"Processing with {agent_name}..."
                    })
                    
                    # Simulate a bit of "thinking" time for visual effect
                    await asyncio.sleep(0.8)
                    
                    # Send the final result from this agent
                    if update_content:
                        await websocket.send_json({
                            "type": "result",
                            "agent": agent_name,
                            "content": update_content
                        })

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
