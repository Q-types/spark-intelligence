"""
Code Review Category Benchmark
Tests all 4 code review problems with scoring

Problems:
- rev_001: Extract Method Refactoring (Easy)
- rev_002: Apply Strategy Pattern (Medium)
- rev_003: Code Review: Find Issues (Medium)
- rev_004: Replace Inheritance with Composition (Hard)
"""

import json
from typing import Optional, Dict, Any, List, Protocol, Callable, runtime_checkable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


# ============= Scoring Infrastructure =============

class ScoreCategory(Enum):
    DESIGN_PATTERN = "design_pattern"
    REFACTORING = "refactoring"
    ISSUE_DETECTION = "issue_detection"
    TESTABILITY = "testability"


@dataclass
class TestResult:
    name: str
    passed: bool
    details: str = ""
    category: ScoreCategory = ScoreCategory.REFACTORING


@dataclass
class ProblemScore:
    problem_id: str
    title: str
    difficulty: str
    tests: List[TestResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if not self.tests:
            return 0.0
        return sum(1 for t in self.tests if t.passed) / len(self.tests)

    @property
    def score(self) -> float:
        weight = {"Easy": 1.0, "Medium": 1.5, "Hard": 2.0}.get(self.difficulty, 1.0)
        return self.pass_rate * 100 * weight

    def add_test(self, name: str, passed: bool, details: str = "",
                 category: ScoreCategory = ScoreCategory.REFACTORING):
        self.tests.append(TestResult(name, passed, details, category))


# ============= Mock Dependencies =============

class MockDB:
    """Mock database for testing."""
    def __init__(self):
        self.orders = MockCollection()


class MockCollection:
    """Mock database collection."""
    def __init__(self):
        self.data = []

    def insert(self, doc):
        self.data.append(doc)
        return {"id": len(self.data)}


class MockEmail:
    """Mock email service."""
    def __init__(self):
        self.sent = []

    def send(self, to: str, message: str):
        self.sent.append({"to": to, "message": message})


# ============= REV_001: Extract Method Refactoring =============

# ORIGINAL CODE (monolithic):
# def process_order(order):
#     # Validate (lines 1-7)
#     # Calculate (lines 8-14)
#     # Save (lines 15-21)
#     # Notify (lines 22-26)
#     return order

# REFACTORED CODE:

class OrderProcessor:
    """
    REV_001: Extract Method Refactoring

    Original 30-line monolithic method refactored into:
    - validate_order(): Validation logic
    - calculate_totals(): Calculation logic
    - save_order(): Persistence logic
    - send_notifications(): Notification logic
    - process_order(): Orchestrates the steps

    Benefits:
    - Single Responsibility Principle
    - Each method is independently testable
    - Clear, self-documenting code
    """

    TAX_RATE = 0.08
    FREE_SHIPPING_THRESHOLD = 50
    SHIPPING_COST = 5.99
    LARGE_ORDER_THRESHOLD = 100

    def __init__(self, db: MockDB, email: MockEmail):
        self.db = db
        self.email = email

    def validate_order(self, order: Dict) -> None:
        """
        Validate order structure and content.
        Raises ValueError for invalid orders.
        """
        if not order.get('items'):
            raise ValueError('No items')
        if not order.get('customer_id'):
            raise ValueError('No customer')

        for item in order['items']:
            if item.get('quantity', 0) <= 0:
                raise ValueError('Invalid quantity')
            if item.get('price', 0) < 0:
                raise ValueError('Invalid price')

    def calculate_totals(self, order: Dict) -> Dict[str, float]:
        """
        Calculate order totals.
        Returns dict with subtotal, tax, shipping, total.
        """
        subtotal = sum(
            item['price'] * item['quantity']
            for item in order['items']
        )

        tax = subtotal * self.TAX_RATE

        shipping = (
            0 if subtotal >= self.FREE_SHIPPING_THRESHOLD
            else self.SHIPPING_COST
        )

        total = subtotal + tax + shipping

        return {
            'subtotal': subtotal,
            'tax': tax,
            'shipping': shipping,
            'total': total
        }

    def save_order(self, order: Dict, totals: Dict[str, float]) -> Dict:
        """
        Persist order to database.
        Returns the saved order with ID.
        """
        order_to_save = {
            **order,
            **totals,
            'status': 'pending'
        }

        result = self.db.orders.insert(order_to_save)
        order_to_save['id'] = result['id']

        return order_to_save

    def send_notifications(self, order: Dict) -> None:
        """
        Send order confirmation emails.
        """
        self.email.send(
            order['customer_id'],
            f"Order {order.get('id', 'NEW')} confirmed"
        )

        if order.get('total', 0) > self.LARGE_ORDER_THRESHOLD:
            self.email.send(
                'sales@company.com',
                f"Large order: {order.get('id', 'NEW')}"
            )

    def process_order(self, order: Dict) -> Dict:
        """
        Main orchestration method.
        Coordinates validation, calculation, persistence, and notification.
        """
        # Step 1: Validate
        self.validate_order(order)

        # Step 2: Calculate
        totals = self.calculate_totals(order)

        # Step 3: Save
        saved_order = self.save_order(order, totals)

        # Step 4: Notify
        self.send_notifications(saved_order)

        return saved_order


def test_rev_001() -> ProblemScore:
    """Test Extract Method Refactoring."""
    score = ProblemScore("rev_001", "Extract Method Refactoring", "Easy")

    db = MockDB()
    email = MockEmail()
    processor = OrderProcessor(db, email)

    # Test 1: Validation is separate and testable
    try:
        processor.validate_order({})
        validation_works = False
    except ValueError as e:
        validation_works = "No items" in str(e)

    score.add_test(
        "validation_extracted",
        validation_works,
        "validate_order() is independently testable",
        ScoreCategory.TESTABILITY
    )

    # Test 2: Calculation is separate and testable
    order = {'items': [{'price': 10, 'quantity': 2}, {'price': 5, 'quantity': 3}]}
    totals = processor.calculate_totals(order)

    expected_subtotal = 35  # 20 + 15
    expected_tax = 35 * 0.08
    expected_shipping = 5.99  # Under $50

    score.add_test(
        "calculation_extracted",
        totals['subtotal'] == expected_subtotal and abs(totals['tax'] - expected_tax) < 0.01,
        f"calculate_totals() returns correct values: {totals}",
        ScoreCategory.TESTABILITY
    )

    # Test 3: Free shipping threshold
    big_order = {'items': [{'price': 60, 'quantity': 1}]}
    totals = processor.calculate_totals(big_order)

    score.add_test(
        "free_shipping_logic",
        totals['shipping'] == 0,
        "Free shipping for orders >= $50",
        ScoreCategory.REFACTORING
    )

    # Test 4: Save is separate
    order = {
        'customer_id': 'cust123',
        'items': [{'price': 10, 'quantity': 1}]
    }
    totals = {'subtotal': 10, 'tax': 0.8, 'shipping': 5.99, 'total': 16.79}
    saved = processor.save_order(order, totals)

    score.add_test(
        "save_extracted",
        saved.get('status') == 'pending' and 'id' in saved,
        "save_order() adds status and ID",
        ScoreCategory.TESTABILITY
    )

    # Test 5: Notifications separate
    order_with_id = {'id': 1, 'customer_id': 'test@example.com', 'total': 150}
    processor.send_notifications(order_with_id)

    score.add_test(
        "notifications_extracted",
        len(email.sent) == 2,  # Customer + sales (large order)
        f"send_notifications() sent {len(email.sent)} emails",
        ScoreCategory.TESTABILITY
    )

    # Test 6: Main method orchestrates
    db2 = MockDB()
    email2 = MockEmail()
    processor2 = OrderProcessor(db2, email2)

    order = {
        'customer_id': 'customer@test.com',
        'items': [{'price': 25, 'quantity': 2}]
    }
    result = processor2.process_order(order)

    score.add_test(
        "orchestration_works",
        result.get('status') == 'pending' and result.get('total') is not None,
        "process_order() coordinates all steps",
        ScoreCategory.REFACTORING
    )

    # Test 7: Methods have single responsibility
    methods = ['validate_order', 'calculate_totals', 'save_order', 'send_notifications']
    all_present = all(hasattr(processor, m) for m in methods)

    score.add_test(
        "srp_followed",
        all_present,
        f"All {len(methods)} extracted methods present",
        ScoreCategory.DESIGN_PATTERN
    )

    return score


# ============= REV_002: Apply Strategy Pattern =============

# ORIGINAL CODE (conditional mess):
# def process_payment(method, amount, details):
#     if method == 'credit_card': ...
#     elif method == 'paypal': ...
#     elif method == 'crypto': ...
#     else: raise ValueError(...)

# REFACTORED CODE:

@runtime_checkable
class PaymentStrategy(Protocol):
    """Strategy interface for payment processing."""

    def validate(self, details: Dict) -> bool:
        """Validate payment details."""
        ...

    def process(self, amount: float, details: Dict) -> Dict:
        """Process the payment and return result."""
        ...


class CreditCardStrategy:
    """
    Credit card payment strategy.
    """
    name = "credit_card"

    def validate(self, details: Dict) -> bool:
        card = details.get('card_number', '')
        # Simplified Luhn check
        return len(card) >= 13 and card.isdigit()

    def process(self, amount: float, details: Dict) -> Dict:
        if not self.validate(details):
            raise ValueError("Invalid card")

        # Mock Stripe charge
        return {
            'success': True,
            'transaction_id': f"ch_{hash(details['card_number']) % 100000}",
            'method': self.name
        }


class PayPalStrategy:
    """
    PayPal payment strategy.
    """
    name = "paypal"

    def validate(self, details: Dict) -> bool:
        email = details.get('paypal_email', '')
        return '@' in email and '.' in email

    def process(self, amount: float, details: Dict) -> Dict:
        if not self.validate(details):
            raise ValueError("Invalid PayPal email")

        return {
            'success': True,
            'redirect_url': f"https://paypal.com/pay/{hash(details['paypal_email']) % 100000}",
            'method': self.name
        }


class CryptoStrategy:
    """
    Cryptocurrency payment strategy.
    """
    name = "crypto"

    def validate(self, details: Dict) -> bool:
        wallet = details.get('wallet_address', '')
        return len(wallet) >= 26  # Basic wallet address length check

    def process(self, amount: float, details: Dict) -> Dict:
        if not self.validate(details):
            raise ValueError("Invalid wallet address")

        return {
            'success': True,
            'invoice_url': f"https://crypto.com/invoice/{hash(details['wallet_address']) % 100000}",
            'method': self.name
        }


class BankTransferStrategy:
    """
    NEW payment method - demonstrates extensibility.
    Added without modifying existing strategies.
    """
    name = "bank_transfer"

    def validate(self, details: Dict) -> bool:
        return bool(details.get('account_number')) and bool(details.get('routing_number'))

    def process(self, amount: float, details: Dict) -> Dict:
        if not self.validate(details):
            raise ValueError("Invalid bank details")

        return {
            'success': True,
            'reference': f"BT-{hash(details['account_number']) % 100000}",
            'method': self.name
        }


class PaymentProcessor:
    """
    REV_002: Strategy Pattern Implementation

    Benefits:
    - Open/Closed Principle: Add new payment methods without modifying existing code
    - Single Responsibility: Each strategy handles one payment type
    - Testable: Strategies can be tested in isolation
    - Extensible: Register new strategies at runtime
    """

    def __init__(self):
        self._strategies: Dict[str, PaymentStrategy] = {}

    def register_strategy(self, name: str, strategy: PaymentStrategy) -> None:
        """Register a payment strategy."""
        self._strategies[name] = strategy

    def get_available_methods(self) -> List[str]:
        """Return list of available payment methods."""
        return list(self._strategies.keys())

    def process_payment(self, method: str, amount: float, details: Dict) -> Dict:
        """
        Process payment using the appropriate strategy.
        Maintains same external API as original.
        """
        if method not in self._strategies:
            raise ValueError(f"Unknown payment method: {method}")

        strategy = self._strategies[method]
        return strategy.process(amount, details)


def create_default_processor() -> PaymentProcessor:
    """Factory function to create processor with default strategies."""
    processor = PaymentProcessor()
    processor.register_strategy("credit_card", CreditCardStrategy())
    processor.register_strategy("paypal", PayPalStrategy())
    processor.register_strategy("crypto", CryptoStrategy())
    return processor


def test_rev_002() -> ProblemScore:
    """Test Strategy Pattern Application."""
    score = ProblemScore("rev_002", "Apply Strategy Pattern", "Medium")

    # Test 1: Strategy interface exists
    score.add_test(
        "strategy_interface",
        isinstance(CreditCardStrategy(), PaymentStrategy),
        "Strategies implement PaymentStrategy protocol",
        ScoreCategory.DESIGN_PATTERN
    )

    # Test 2: Credit card strategy works
    processor = create_default_processor()
    result = processor.process_payment(
        "credit_card",
        100.00,
        {"card_number": "4111111111111111"}
    )

    score.add_test(
        "credit_card_strategy",
        result['success'] and 'transaction_id' in result,
        f"Credit card result: {result}",
        ScoreCategory.REFACTORING
    )

    # Test 3: PayPal strategy works
    result = processor.process_payment(
        "paypal",
        50.00,
        {"paypal_email": "test@example.com"}
    )

    score.add_test(
        "paypal_strategy",
        result['success'] and 'redirect_url' in result,
        f"PayPal result: {result}",
        ScoreCategory.REFACTORING
    )

    # Test 4: Crypto strategy works
    result = processor.process_payment(
        "crypto",
        25.00,
        {"wallet_address": "0x1234567890abcdef1234567890abcdef"}
    )

    score.add_test(
        "crypto_strategy",
        result['success'] and 'invoice_url' in result,
        f"Crypto result: {result}",
        ScoreCategory.REFACTORING
    )

    # Test 5: Unknown method raises error
    try:
        processor.process_payment("unknown", 10.00, {})
        unknown_raises = False
    except ValueError as e:
        unknown_raises = "Unknown payment method" in str(e)

    score.add_test(
        "unknown_method_error",
        unknown_raises,
        "Unknown method raises ValueError",
        ScoreCategory.REFACTORING
    )

    # Test 6: Can add new strategy without modifying existing code (OCP)
    processor.register_strategy("bank_transfer", BankTransferStrategy())
    result = processor.process_payment(
        "bank_transfer",
        200.00,
        {"account_number": "123456789", "routing_number": "987654321"}
    )

    score.add_test(
        "extensibility_ocp",
        result['success'] and result['method'] == 'bank_transfer',
        "New payment method added without modifying existing strategies",
        ScoreCategory.DESIGN_PATTERN
    )

    # Test 7: Strategies are independently testable
    cc_strategy = CreditCardStrategy()
    valid = cc_strategy.validate({"card_number": "4111111111111111"})
    invalid = cc_strategy.validate({"card_number": "invalid"})

    score.add_test(
        "strategies_testable",
        valid and not invalid,
        "Individual strategies can be unit tested",
        ScoreCategory.TESTABILITY
    )

    # Test 8: Get available methods
    methods = processor.get_available_methods()

    score.add_test(
        "list_methods",
        len(methods) == 4 and "credit_card" in methods,
        f"Available methods: {methods}",
        ScoreCategory.REFACTORING
    )

    return score


# ============= REV_003: Code Review - Find Issues =============

# CODE TO REVIEW:
"""
import os
import pickle

def load_user_data(username):
    path = f'/data/users/{username}.pkl'
    if os.path.exists(path):
        with open(path) as f:
            data = pickle.load(f)
        return data
    return None

def save_user_data(username, data):
    path = f'/data/users/{username}.pkl'
    with open(path, 'w') as f:
        pickle.dump(data, f)

def authenticate(username, password):
    user = load_user_data(username)
    if user and user['password'] == password:
        return True
    return False

def get_user_file(username, filename):
    path = f'/data/users/{username}/{filename}'
    with open(path) as f:
        return f.read()
"""

@dataclass
class CodeIssue:
    """Represents an issue found in code review."""
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    category: str  # security, bug, performance, style
    location: str
    description: str
    fix: str


class CodeReviewer:
    """
    REV_003: Code Review - Find Issues

    Identifies security vulnerabilities, bugs, performance issues, and style violations.
    """

    def review_code(self) -> List[CodeIssue]:
        """
        Return all issues found in the code.
        """
        return [
            # SECURITY ISSUES

            CodeIssue(
                severity="CRITICAL",
                category="security",
                location="load_user_data/save_user_data",
                description="Path Traversal Vulnerability: username is directly interpolated into path. "
                           "Attacker can use '../' to access arbitrary files (e.g., username='../../../etc/passwd')",
                fix="Validate username: reject if contains '/', '..', or other path characters. "
                    "Use os.path.basename() or sanitize input."
            ),

            CodeIssue(
                severity="CRITICAL",
                category="security",
                location="load_user_data/save_user_data",
                description="Pickle Deserialization Vulnerability: pickle.load() can execute arbitrary code. "
                           "Malicious pickle files can lead to Remote Code Execution (RCE).",
                fix="Use safer serialization like JSON. If pickle required, use hmac to verify integrity "
                    "or cryptographic signatures."
            ),

            CodeIssue(
                severity="CRITICAL",
                category="security",
                location="authenticate",
                description="Plaintext Password Storage: Passwords stored as plaintext in user data. "
                           "Database breach exposes all passwords.",
                fix="Use password hashing (bcrypt, argon2). Store hash, verify with constant-time comparison."
            ),

            CodeIssue(
                severity="HIGH",
                category="security",
                location="authenticate",
                description="Timing Attack Vulnerability: String comparison '==' is not constant-time. "
                           "Attacker can infer password length/characters by measuring response time.",
                fix="Use hmac.compare_digest() or secrets.compare_digest() for timing-safe comparison."
            ),

            CodeIssue(
                severity="CRITICAL",
                category="security",
                location="get_user_file",
                description="Path Traversal in filename: filename parameter directly in path allows "
                           "reading arbitrary files (e.g., filename='../../../etc/passwd').",
                fix="Validate filename, use os.path.basename(), check resolved path is within allowed directory."
            ),

            # BUGS

            CodeIssue(
                severity="HIGH",
                category="bug",
                location="load_user_data",
                description="Wrong file mode: pickle.load() requires binary mode ('rb'), but file opened in text mode.",
                fix="Change open(path) to open(path, 'rb')"
            ),

            CodeIssue(
                severity="HIGH",
                category="bug",
                location="save_user_data",
                description="Wrong file mode: pickle.dump() requires binary mode ('wb'), but file opened with 'w' (text).",
                fix="Change open(path, 'w') to open(path, 'wb')"
            ),

            CodeIssue(
                severity="MEDIUM",
                category="bug",
                location="load_user_data",
                description="No error handling: If file exists but is corrupted, pickle.load() raises exception "
                           "that propagates to caller.",
                fix="Wrap in try/except, handle UnpicklingError, return None or raise custom exception."
            ),

            CodeIssue(
                severity="MEDIUM",
                category="bug",
                location="authenticate",
                description="No KeyError handling: If user dict doesn't have 'password' key, raises KeyError.",
                fix="Use user.get('password') instead of user['password']."
            ),

            # PERFORMANCE

            CodeIssue(
                severity="LOW",
                category="performance",
                location="load_user_data",
                description="os.path.exists() + open() race condition: File could be deleted between check and open.",
                fix="Remove exists() check, use try/except FileNotFoundError instead (EAFP pattern)."
            ),

            # STYLE

            CodeIssue(
                severity="LOW",
                category="style",
                location="all functions",
                description="No type hints: Functions lack type annotations, reducing IDE support and documentation.",
                fix="Add type hints: def load_user_data(username: str) -> Optional[Dict]: ..."
            ),

            CodeIssue(
                severity="LOW",
                category="style",
                location="all functions",
                description="No docstrings: Functions lack documentation.",
                fix="Add docstrings describing purpose, parameters, return values, and exceptions."
            ),
        ]

    def get_issues_by_severity(self, severity: str) -> List[CodeIssue]:
        """Get issues filtered by severity."""
        return [i for i in self.review_code() if i.severity == severity]

    def get_issues_by_category(self, category: str) -> List[CodeIssue]:
        """Get issues filtered by category."""
        return [i for i in self.review_code() if i.category == category]

    def summary(self) -> Dict[str, int]:
        """Get summary of issues by severity."""
        issues = self.review_code()
        return {
            "CRITICAL": len([i for i in issues if i.severity == "CRITICAL"]),
            "HIGH": len([i for i in issues if i.severity == "HIGH"]),
            "MEDIUM": len([i for i in issues if i.severity == "MEDIUM"]),
            "LOW": len([i for i in issues if i.severity == "LOW"]),
            "total": len(issues)
        }


def test_rev_003() -> ProblemScore:
    """Test Code Review Issue Detection."""
    score = ProblemScore("rev_003", "Code Review: Find Issues", "Medium")

    reviewer = CodeReviewer()
    issues = reviewer.review_code()
    summary = reviewer.summary()

    # Test 1: Path traversal identified
    path_traversal = any(
        "path traversal" in i.description.lower()
        for i in issues
    )
    score.add_test(
        "path_traversal_found",
        path_traversal,
        "Path traversal vulnerability identified",
        ScoreCategory.ISSUE_DETECTION
    )

    # Test 2: Pickle vulnerability identified
    pickle_vuln = any(
        "pickle" in i.description.lower() and "security" in i.category
        for i in issues
    )
    score.add_test(
        "pickle_vulnerability_found",
        pickle_vuln,
        "Pickle deserialization vulnerability identified",
        ScoreCategory.ISSUE_DETECTION
    )

    # Test 3: Plaintext password identified
    plaintext_pwd = any(
        "password" in i.description.lower() and "plaintext" in i.description.lower()
        for i in issues
    )
    score.add_test(
        "plaintext_password_found",
        plaintext_pwd,
        "Plaintext password storage identified",
        ScoreCategory.ISSUE_DETECTION
    )

    # Test 4: File mode bugs identified
    file_mode_bugs = len([
        i for i in issues
        if "mode" in i.description.lower() and i.category == "bug"
    ])
    score.add_test(
        "file_mode_bugs_found",
        file_mode_bugs >= 2,
        f"Found {file_mode_bugs} file mode bugs (need binary mode)",
        ScoreCategory.ISSUE_DETECTION
    )

    # Test 5: All issues have fixes
    all_have_fixes = all(bool(i.fix) for i in issues)
    score.add_test(
        "fixes_provided",
        all_have_fixes,
        f"All {len(issues)} issues have suggested fixes",
        ScoreCategory.ISSUE_DETECTION
    )

    # Test 6: Critical issues identified
    critical_count = summary["CRITICAL"]
    score.add_test(
        "critical_issues_found",
        critical_count >= 4,
        f"Found {critical_count} CRITICAL issues",
        ScoreCategory.ISSUE_DETECTION
    )

    # Test 7: Security category issues
    security_issues = reviewer.get_issues_by_category("security")
    score.add_test(
        "security_issues_categorized",
        len(security_issues) >= 5,
        f"Found {len(security_issues)} security issues",
        ScoreCategory.ISSUE_DETECTION
    )

    # Test 8: Summary includes all severities
    has_all_severities = all(
        sev in summary
        for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "total"]
    )
    score.add_test(
        "severity_rating",
        has_all_severities and summary["total"] >= 10,
        f"Summary: {summary}",
        ScoreCategory.ISSUE_DETECTION
    )

    return score


# ============= REV_004: Replace Inheritance with Composition =============

# ORIGINAL CODE (problematic inheritance):
# class Animal -> Mammal -> FlyingMammal -> Bat
# class Animal -> Bird -> SwimmingBird -> Penguin
# Problem: What about flying birds? Swimming mammals?

# REFACTORED CODE using Composition:

# Capability Protocols
@runtime_checkable
class Flyable(Protocol):
    def fly(self) -> str: ...


@runtime_checkable
class Swimmable(Protocol):
    def swim(self) -> str: ...


@runtime_checkable
class Reproducible(Protocol):
    def reproduce(self) -> str: ...


# Capability Implementations (Composition components)
class FlightCapability:
    """Flight capability that can be composed into any animal."""

    def __init__(self, style: str = "flapping"):
        self.style = style

    def fly(self) -> str:
        return f"Flying by {self.style}"


class SwimmingCapability:
    """Swimming capability that can be composed into any animal."""

    def __init__(self, style: str = "paddling"):
        self.style = style

    def swim(self) -> str:
        return f"Swimming by {self.style}"


class LiveBirthCapability:
    """Live birth reproduction (mammals)."""

    def reproduce(self) -> str:
        return "Live birth"


class EggLayingCapability:
    """Egg-laying reproduction (birds, reptiles)."""

    def reproduce(self) -> str:
        return "Lays eggs"


# Base Animal with Composition
class Animal:
    """
    REV_004: Composition-based Animal

    Instead of inheritance hierarchy, animals are composed of capabilities.
    Any combination of capabilities is possible.

    Benefits:
    - Flexibility: Any capability combination without class explosion
    - Cohesion: Capabilities are self-contained
    - Testability: Capabilities can be tested independently
    - No diamond problem or deep hierarchies
    """

    def __init__(
        self,
        name: str,
        species: str,
        flight: Optional[FlightCapability] = None,
        swimming: Optional[SwimmingCapability] = None,
        reproduction: Optional[Reproducible] = None
    ):
        self.name = name
        self.species = species
        self._flight = flight
        self._swimming = swimming
        self._reproduction = reproduction

    @property
    def can_fly(self) -> bool:
        return self._flight is not None

    @property
    def can_swim(self) -> bool:
        return self._swimming is not None

    def fly(self) -> str:
        if self._flight is None:
            raise NotImplementedError(f"{self.species} cannot fly")
        return self._flight.fly()

    def swim(self) -> str:
        if self._swimming is None:
            raise NotImplementedError(f"{self.species} cannot swim")
        return self._swimming.swim()

    def reproduce(self) -> str:
        if self._reproduction is None:
            raise NotImplementedError(f"{self.species} reproduction not defined")
        return self._reproduction.reproduce()

    def describe(self) -> str:
        capabilities = []
        if self.can_fly:
            capabilities.append("can fly")
        if self.can_swim:
            capabilities.append("can swim")
        return f"{self.name} the {self.species}: {', '.join(capabilities) or 'no special abilities'}"


# Factory functions for common animal types
def create_bat(name: str) -> Animal:
    """Create a bat (flying mammal)."""
    return Animal(
        name=name,
        species="Bat",
        flight=FlightCapability(style="echolocation-guided flapping"),
        reproduction=LiveBirthCapability()
    )


def create_penguin(name: str) -> Animal:
    """Create a penguin (swimming bird)."""
    return Animal(
        name=name,
        species="Penguin",
        swimming=SwimmingCapability(style="wing-propelled diving"),
        reproduction=EggLayingCapability()
    )


def create_duck(name: str) -> Animal:
    """Create a duck (flying AND swimming bird)."""
    return Animal(
        name=name,
        species="Duck",
        flight=FlightCapability(style="rapid wing beats"),
        swimming=SwimmingCapability(style="webbed feet paddling"),
        reproduction=EggLayingCapability()
    )


def create_whale(name: str) -> Animal:
    """Create a whale (swimming mammal)."""
    return Animal(
        name=name,
        species="Whale",
        swimming=SwimmingCapability(style="tail flukes"),
        reproduction=LiveBirthCapability()
    )


def create_flying_fish(name: str) -> Animal:
    """Create a flying fish (flying AND swimming)."""
    return Animal(
        name=name,
        species="Flying Fish",
        flight=FlightCapability(style="gliding"),
        swimming=SwimmingCapability(style="fin propulsion"),
        reproduction=EggLayingCapability()
    )


def test_rev_004() -> ProblemScore:
    """Test Composition over Inheritance."""
    score = ProblemScore("rev_004", "Replace Inheritance with Composition", "Hard")

    # Test 1: Bat can fly but not swim (like original)
    bat = create_bat("Bruce")
    can_fly = "fly" in bat.fly().lower()
    try:
        bat.swim()
        cannot_swim = False
    except NotImplementedError:
        cannot_swim = True

    score.add_test(
        "bat_capabilities",
        can_fly and cannot_swim,
        "Bat can fly, cannot swim",
        ScoreCategory.REFACTORING
    )

    # Test 2: Penguin can swim but not fly (like original)
    penguin = create_penguin("Penny")
    can_swim = "swim" in penguin.swim().lower()
    try:
        penguin.fly()
        cannot_fly = False
    except NotImplementedError:
        cannot_fly = True

    score.add_test(
        "penguin_capabilities",
        can_swim and cannot_fly,
        "Penguin can swim, cannot fly",
        ScoreCategory.REFACTORING
    )

    # Test 3: Duck can BOTH fly and swim (impossible with original hierarchy!)
    duck = create_duck("Donald")
    duck_flies = duck.can_fly and "fly" in duck.fly().lower()
    duck_swims = duck.can_swim and "swim" in duck.swim().lower()

    score.add_test(
        "duck_both_capabilities",
        duck_flies and duck_swims,
        "Duck can BOTH fly and swim - impossible with inheritance!",
        ScoreCategory.DESIGN_PATTERN
    )

    # Test 4: Whale is swimming mammal (another combination)
    whale = create_whale("Willy")
    whale_swims = "swim" in whale.swim().lower()
    whale_birth = "live birth" in whale.reproduce().lower()

    score.add_test(
        "whale_swimming_mammal",
        whale_swims and whale_birth,
        "Whale: swimming + live birth (mammal)",
        ScoreCategory.REFACTORING
    )

    # Test 5: Flying fish - yet another combination
    flying_fish = create_flying_fish("Finn")

    score.add_test(
        "flying_fish_both",
        flying_fish.can_fly and flying_fish.can_swim,
        "Flying fish: both fly and swim capabilities",
        ScoreCategory.DESIGN_PATTERN
    )

    # Test 6: Capabilities are independently testable
    flight = FlightCapability(style="soaring")
    swimming = SwimmingCapability(style="diving")

    score.add_test(
        "capabilities_testable",
        "soaring" in flight.fly() and "diving" in swimming.swim(),
        "Capability classes are independently testable",
        ScoreCategory.TESTABILITY
    )

    # Test 7: No deep inheritance hierarchy
    # Animal class doesn't inherit from anything complex
    mro = Animal.__mro__
    score.add_test(
        "no_deep_hierarchy",
        len(mro) == 2,  # Animal -> object
        f"Animal MRO: {[c.__name__ for c in mro]} (flat)",
        ScoreCategory.DESIGN_PATTERN
    )

    # Test 8: Clean API maintained
    description = duck.describe()
    score.add_test(
        "clean_api",
        "fly" in description and "swim" in description,
        f"Clean describe() API: {description}",
        ScoreCategory.REFACTORING
    )

    return score


# ============= Benchmark Runner =============

def run_code_review_benchmark() -> Dict[str, Any]:
    """Run all code review benchmarks and return results."""
    print("=" * 70)
    print("CODE REVIEW CATEGORY BENCHMARK")
    print("=" * 70)

    results = []

    tests = [
        ("REV_001", test_rev_001),
        ("REV_002", test_rev_002),
        ("REV_003", test_rev_003),
        ("REV_004", test_rev_004),
    ]

    total_score = 0
    max_score = 0

    for problem_id, test_func in tests:
        print(f"\n{'-' * 50}")
        print(f"Running {problem_id}...")
        print(f"{'-' * 50}")

        problem_score = test_func()
        results.append(problem_score)

        for test in problem_score.tests:
            status = "✓" if test.passed else "✗"
            print(f"  {status} {test.name}: {test.details}")

        print(f"\n  Pass Rate: {problem_score.pass_rate:.1%}")
        print(f"  Score: {problem_score.score:.1f}")

        total_score += problem_score.score
        weight = {"Easy": 1.0, "Medium": 1.5, "Hard": 2.0}.get(problem_score.difficulty, 1.0)
        max_score += 100 * weight

    # Summary
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)

    print("\n| Problem | Difficulty | Pass Rate | Score |")
    print("|---------|------------|-----------|-------|")

    for s in results:
        print(f"| {s.problem_id} | {s.difficulty} | {s.pass_rate:.1%} | {s.score:.1f} |")

    overall = (total_score / max_score * 100) if max_score > 0 else 0
    print(f"\n**Overall Score: {overall:.1f}% ({total_score:.1f}/{max_score:.1f})**")

    # Category breakdown
    all_tests = [t for s in results for t in s.tests]
    design = [t for t in all_tests if t.category == ScoreCategory.DESIGN_PATTERN]
    refactor = [t for t in all_tests if t.category == ScoreCategory.REFACTORING]
    issues = [t for t in all_tests if t.category == ScoreCategory.ISSUE_DETECTION]
    testability = [t for t in all_tests if t.category == ScoreCategory.TESTABILITY]

    print(f"\nDesign Pattern Tests: {sum(1 for t in design if t.passed)}/{len(design)} passed")
    print(f"Refactoring Tests: {sum(1 for t in refactor if t.passed)}/{len(refactor)} passed")
    print(f"Issue Detection Tests: {sum(1 for t in issues if t.passed)}/{len(issues)} passed")
    print(f"Testability Tests: {sum(1 for t in testability if t.passed)}/{len(testability)} passed")

    return {
        "problems": [
            {
                "id": s.problem_id,
                "title": s.title,
                "difficulty": s.difficulty,
                "pass_rate": s.pass_rate,
                "score": s.score,
                "tests": [
                    {"name": t.name, "passed": t.passed, "details": t.details}
                    for t in s.tests
                ]
            }
            for s in results
        ],
        "summary": {
            "total_score": total_score,
            "max_score": max_score,
            "overall_percentage": overall,
        }
    }


if __name__ == "__main__":
    results = run_code_review_benchmark()

    output_path = "/tmp/code_review_benchmark_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")
