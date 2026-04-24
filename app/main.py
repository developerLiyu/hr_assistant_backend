import os

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from app.api.v1 import system, position, resume, screening, interview_question, recordings, interview_summary, \
    interview_evaluation
from app.utils import exception_handlers

app = FastAPI(
    title="HR智能助手API",
    description="企业HR智能助手后端接口",
    version="1.0.0"
)

# 应用异常处理器
exception_handlers.register_exception_handler(app)

# 设置允许的来源（可以是域名列表）
origins = [
    "http://localhost:5173"
]
# 添加跨域处理CORS中间件
app.add_middleware(
    CORSMiddleware,  # 使用CORSMiddleware
    allow_origins=origins,  # 允许的来源
    allow_credentials=True,  # 是否允许携带cookie
    allow_methods=["*"],  # 允许的请求方法
    allow_headers=["*"],  # 允许的请求头
)

@app.get("/")
async def root():
    return {"message": "HR智能助手API运行中", "docs": "/docs"}

# 注册路由
app.include_router(system.router)
app.include_router(position.router)
app.include_router(resume.router)
app.include_router(screening.router)
app.include_router(interview_question.router)
app.include_router(recordings.router)
app.include_router(interview_summary.router)
app.include_router(interview_evaluation.router)


