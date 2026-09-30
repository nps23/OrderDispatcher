import pydantic
import uuid
import enum

class OrderCategory(enum.Enum):
    UNKNOWN=1
    COLD_SANDWHICHES=2
    HOT_SANDWHICHES=3
    PASTERIES=4
    BEVERAGE=5
    LUNCH_AND_DINNER=6
    CHICKEN=7
    APPETIZERS=8
    DESSERTS=9
    SIDE=10
    BREAKFAST=11
    
class OrderStatus(enum.Enum):
    UNKNOWN=1
    DELIVERED=2
    WITH_COURIER=3
    IN_PROGRESS=4



class Order(pydantic.BaseModel):
    uuid: uuid.UUID
    name: str
    catagory: OrderCategory
    price: float
    status: OrderStatus
