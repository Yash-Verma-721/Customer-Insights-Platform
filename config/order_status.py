class OrderStatus:
    PENDING = "Pending"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"

class VendorOrderStatus:
    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    PACKED = "Packed"
    SHIPPED = "Shipped"
    DELIVERED = "Delivered"
    CANCELLED = "Cancelled"
    RETURNED = "Returned"
    REFUNDED = "Refunded"

    @classmethod
    def all_statuses(cls):
        return [
            cls.PENDING, cls.CONFIRMED, cls.PACKED, cls.SHIPPED,
            cls.DELIVERED, cls.CANCELLED, cls.RETURNED, cls.REFUNDED
        ]
