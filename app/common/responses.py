"""Base schema shared by every request/response model.

Python code uses snake_case (employee_code); the JSON the frontend sees is camelCase (employeeCode).
Requests are accepted in either style.
"""
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
