from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
import logging
from datetime import datetime
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Quiz Solver API")


class QuizRequest(BaseModel):
    email: EmailStr
    secret: str
    url: str


class QuizResponse(BaseModel):
    status: str
    message: str
    timestamp: str


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "Quiz Solver API",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/solve", response_model=QuizResponse)
async def solve_quiz(request: QuizRequest, background_tasks: BackgroundTasks):
    """
    Main endpoint to receive quiz URLs and start solving
    """
    logger.info(f"Received request for quiz: {request.url}")
    
    # Verify secret
    if request.secret != config.SECRET:
        logger.warning(f"Invalid secret provided for email: {request.email}")
        raise HTTPException(status_code=403, detail="Invalid secret")
    
    # Verify email
    if request.email != config.EMAIL:
        logger.warning(f"Email mismatch: {request.email} != {config.EMAIL}")
        raise HTTPException(status_code=403, detail="Email does not match")
    
    logger.info(f"Authentication successful for {request.email}")
    
    # Start solving the quiz in the background
    # This allows us to respond with 200 immediately
    # while processing takes place
    background_tasks.add_task(solve_quiz_chain, request.url, request.email, request.secret)
    
    return QuizResponse(
        status="accepted",
        message=f"Quiz solving started for {request.url}",
        timestamp=datetime.now().isoformat()
    )


async def solve_quiz_chain(start_url: str, email: str, secret: str):
    """
    Main quiz solving logic - chains through multiple quizzes
    """
    from solver import QuizSolver
    
    logger.info(f"Starting quiz chain from {start_url}")
    
    try:
        solver = QuizSolver(email, secret)
        await solver.solve_chain(start_url)
        logger.info("Quiz chain completed successfully")
    except Exception as e:
        logger.error(f"Error solving quiz chain: {e}", exc_info=True)


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on {config.HOST}:{config.PORT}")
    uvicorn.run(app, host=config.HOST, port=config.PORT)