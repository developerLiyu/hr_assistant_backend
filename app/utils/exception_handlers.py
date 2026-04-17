from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.utils.exception import http_exception_handler, integrity_error_handler, sqlalchemy_error_handler, \
    general_exception_handler


def register_exception_handler(app):
    """
    注册异常处理
    规范：子类在前，父类在后；具体在前，抽象在后
    """
    app.add_exception_handler(HTTPException, http_exception_handler) # 业务异常
    app.add_exception_handler(IntegrityError, integrity_error_handler) # 数据库约束异常
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler) # 数据库异常
    app.add_exception_handler(Exception, general_exception_handler) # 其他情况异常
