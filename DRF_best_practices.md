# Django REST Framework – Best Practices

This document defines **architectural and coding best practices** for Django projects using **Django REST Framework (DRF)**. It is intended to be used as a **review checklist** for automated or manual code review.

---

## 1. Core Architectural Principles

* Follow **separation of concerns** strictly
* Keep HTTP, business logic, and persistence clearly separated
* Prefer **explicitness over magic**
* Treat the **database as the source of truth** for consistency
* Design for **concurrency and failure** by default

Layered responsibility:

```
Views (HTTP layer)
↓
Services (application / business layer)
↓
Models (domain layer)
↓
Database (infrastructure)
```

Dependencies must always point **downwards**, never upwards.

---

## 2. Views – HTTP Layer

### Responsibilities

Views are responsible for:

* Receiving HTTP requests
* Triggering authentication and permission checks
* Calling application services
* Returning HTTP responses

Views must **not**:

* Contain business rules
* Perform complex ORM logic
* Manage transactions

---

### Best Practices for Views

* Keep views **thin and declarative**
* Prefer **APIView / ViewSet** over function-based views for non-trivial endpoints
* Delegate all business actions to services
* Handle only:

  * request parsing
  * response formatting
  * exception-to-HTTP mapping

Example:

```python
class PayOrderView(APIView):
    def post(self, request, pk):
        pay_order(order_id=pk, user=request.user)
        return Response(status=204)
```

### Anti-Patterns

* Business logic inside views
* Conditional domain rules in views
* ORM updates directly in views

---

## 3. Services – Business Logic Layer

### Purpose

Services implement **application use cases** and represent the **core business logic**.

They orchestrate:

* multiple models
* transactions
* side effects

---

### Structure

Recommended layout:

```
app/
├── services/
│   ├── __init__.py
│   ├── order_creation.py
│   ├── order_payment.py
│   ├── order_cancellation.py
│   └── exceptions.py
```

---

### Best Practices for Services

* Use **pure functions**, not classes (unless state is required)
* Accept **explicit arguments only**
* Never accept `request`, serializers, or HTTP objects
* Wrap state-changing logic in `transaction.atomic`
* Raise **domain-specific exceptions**

Example:

```python
@transaction.atomic
def pay_order(*, order_id: int, user: User):
    order = (
        Order.objects
        .select_for_update()
        .get(id=order_id)
    )

    if not order.can_be_paid():
        raise DomainError("Order cannot be paid")

    order.mark_as_paid()
```

---

### Anti-Patterns

* Services calling views or serializers
* Services returning HTTP responses
* Services relying on implicit global state

---

## 4. Models – Domain Layer

### Responsibilities

Models represent **domain entities** and must:

* enforce invariants
* contain domain-level rules
* encapsulate state transitions

---

### Best Practices for Models

* Put **state validation** close to the data
* Use expressive domain methods
* Avoid cross-model orchestration

Example:

```python
class Order(models.Model):
    status = models.CharField(...)

    def can_be_paid(self) -> bool:
        return self.status == OrderStatus.NEW

    def mark_as_paid(self):
        if not self.can_be_paid():
            raise DomainError()
        self.status = OrderStatus.PAID
        self.save()
```

---

## 5. Serializers – Validation & Transformation Layer

### Purpose

Serializers are responsible for:

* validating incoming data
* transforming Python objects to API representations

They must **not** execute business logic.

---

### Best Practices for Serializers

* Use serializers strictly for:

  * input validation
  * output formatting
* Prefer `ModelSerializer` for standard CRUD
* Separate read and write serializers if needed
* Keep `create()` / `update()` minimal

Example:

```python
class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ("product_id", "quantity")
```

---

### Anti-Patterns

* Performing state transitions in serializers
* Calling services from serializers
* Complex ORM logic inside `save()`

---

## 6. Concurrency – Prevention and Handling

Concurrency issues arise whenever **multiple requests operate on the same data concurrently**.

All critical concurrency guarantees must be enforced at the **database level**.

---

### Transaction Management

* Use `transaction.atomic` for all state-changing business operations
* Never rely on Django's default autocommit for complex workflows

Example:

```python
@transaction.atomic
def cancel_order(order_id: int):
    order = Order.objects.select_for_update().get(id=order_id)
    order.cancel()
```

---

### Row-Level Locking

* Use `select_for_update()` when:

  * changing state
  * preventing double execution
  * protecting critical sections

This prevents:

* double payments
* duplicate processing
* lost updates

---

### Database Constraints

* Enforce uniqueness at the database level
* Never rely solely on application-level checks

```python
number = models.CharField(unique=True)
```

Always catch `IntegrityError` explicitly.

---

### Atomic Updates

Avoid read-modify-write patterns:

❌ Unsafe:

```python
obj.value += 1
obj.save()
```

✔ Safe:

```python
Model.objects.filter(id=obj.id).update(
    value=F("value") + 1
)
```

---

### Long-Running Operations

* Never perform external calls inside a transaction
* Use `transaction.on_commit()` for side effects

Example:

```python
transaction.on_commit(lambda: send_email(order))
```

---

### Signals and Concurrency

* Signals must be **reactive only**
* Signals must never modify core business state

Anti-pattern:

* state changes inside `post_save` handlers

---

## 7. Error Handling & Domain Exceptions

### Purpose

A clear exception strategy ensures:

* predictable API behavior
* separation of business and technical failures
* consistent error responses

---

### Exception Categories

* **Domain Errors** – business rule violations
* **Application Errors** – invalid workflows or states
* **Infrastructure Errors** – database, network, external services

---

### Best Practices

* Define domain-specific exceptions
* Never raise HTTP exceptions from services
* Map exceptions to HTTP responses in views or global handlers

Example:

```python
class DomainError(Exception):
    pass
```

```python
try:
    pay_order(order_id=pk, user=request.user)
except DomainError as e:
    return Response({"detail": str(e)}, status=400)
```

---

### Anti-Patterns

* Raising `ValidationError` inside services
* Catching generic `Exception`
* Returning HTTP responses from services

---

## 8. Permissions & Authorization

### Purpose

Authorization defines **who is allowed to perform an action**.

It must be clearly separated from business rules.

---

### Responsibility Split

* **Permissions**: "May this user access this resource?"
* **Business rules**: "Is this operation valid now?"

---

### Best Practices

* Use DRF permissions for access control
* Use object-level permissions when needed
* Keep permission logic declarative and reusable

Example:

```python
class IsOrderOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
```

---

### Anti-Patterns

* Permission checks inside serializers
* Duplicated permission logic across views
* Mixing permission checks with business state validation

---

## 9. Testing Strategy

### Purpose

Testing ensures:

* safe refactoring
* protection against regressions
* confidence in concurrency handling

---

### Test Types

* **Unit tests** – models and services
* **Integration tests** – API endpoints
* **Concurrency tests** – race conditions and locking

---

### Best Practices

* Test services independently from HTTP
* Test domain rules at model level
* Use database transactions in tests

Example:

```python
@pytest.mark.django_db
def test_order_cannot_be_paid_twice():
    order = OrderFactory(status=PAID)
    with pytest.raises(DomainError):
        pay_order(order_id=order.id, user=order.user)
```

---

### Anti-Patterns

* Testing only views
* Skipping concurrency scenarios
* Relying solely on manual testing

---

## 10. Summary Rules (Checklist)

* Views are thin and HTTP-focused
* Services own business logic
* Models enforce domain invariants
* Serializers validate and transform only
* Transactions protect state
* Permissions control access, not business flow
* Exceptions are explicit and categorized
* Database enforces consistency
* Concurrency is handled deliberately

---

**Any deviation from these rules must be explicitly justified and documented.**
