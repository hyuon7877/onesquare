"""
Decimal 처리 공통 유틸리티
15개 모듈에서 사용되는 Decimal 기능 통합
"""

from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN, ROUND_UP, InvalidOperation
import math


def safe_decimal(value, default=Decimal('0')):
    """안전한 Decimal 변환"""
    if value is None:
        return default
    
    try:
        if isinstance(value, Decimal):
            return value
        elif isinstance(value, (int, float)):
            return Decimal(str(value))
        elif isinstance(value, str):
            # 쉼표 제거 및 공백 제거
            cleaned = value.replace(',', '').strip()
            if not cleaned:
                return default
            return Decimal(cleaned)
        else:
            return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default


def format_currency(amount, currency='₩', decimal_places=0):
    """통화 포맷팅"""
    if amount is None:
        return f"{currency}0"
    
    decimal_amount = safe_decimal(amount)
    
    # 천단위 구분자 추가
    if decimal_places == 0:
        formatted = f"{int(decimal_amount):,}"
    else:
        formatted = f"{decimal_amount:,.{decimal_places}f}"
    
    return f"{currency}{formatted}"


def format_percentage(value, decimal_places=1):
    """백분율 포맷팅"""
    if value is None:
        return "0%"
    
    decimal_value = safe_decimal(value)
    percentage = decimal_value * 100
    
    if decimal_places == 0:
        return f"{int(percentage)}%"
    else:
        return f"{percentage:.{decimal_places}f}%"


def round_decimal(value, decimal_places=2, rounding=ROUND_HALF_UP):
    """Decimal 반올림"""
    if value is None:
        return Decimal('0')
    
    decimal_value = safe_decimal(value)
    quantize_value = Decimal('0.1') ** decimal_places
    
    return decimal_value.quantize(quantize_value, rounding=rounding)


def calculate_percentage(part, whole, decimal_places=2):
    """백분율 계산"""
    if not whole or whole == 0:
        return Decimal('0')
    
    part_decimal = safe_decimal(part)
    whole_decimal = safe_decimal(whole)
    
    percentage = (part_decimal / whole_decimal) * 100
    return round_decimal(percentage, decimal_places)


def calculate_ratio(numerator, denominator, decimal_places=2):
    """비율 계산"""
    if not denominator or denominator == 0:
        return Decimal('0')
    
    num_decimal = safe_decimal(numerator)
    denom_decimal = safe_decimal(denominator)
    
    ratio = num_decimal / denom_decimal
    return round_decimal(ratio, decimal_places)


def add_decimals(*values):
    """여러 Decimal 값 더하기"""
    total = Decimal('0')
    for value in values:
        total += safe_decimal(value)
    return total


def subtract_decimals(minuend, *subtrahends):
    """Decimal 값 빼기"""
    result = safe_decimal(minuend)
    for subtrahend in subtrahends:
        result -= safe_decimal(subtrahend)
    return result


def multiply_decimals(*values):
    """여러 Decimal 값 곱하기"""
    if not values:
        return Decimal('0')
    
    result = Decimal('1')
    for value in values:
        result *= safe_decimal(value)
    return result


def divide_decimals(dividend, divisor, decimal_places=2):
    """Decimal 나누기 (0으로 나누기 방지)"""
    if not divisor or safe_decimal(divisor) == 0:
        return Decimal('0')
    
    result = safe_decimal(dividend) / safe_decimal(divisor)
    return round_decimal(result, decimal_places)


def calculate_average(values, decimal_places=2):
    """평균 계산"""
    if not values:
        return Decimal('0')
    
    decimal_values = [safe_decimal(v) for v in values]
    total = sum(decimal_values)
    average = total / len(decimal_values)
    
    return round_decimal(average, decimal_places)


def calculate_sum(values):
    """합계 계산"""
    return sum(safe_decimal(v) for v in values)


def calculate_min(values):
    """최솟값 계산"""
    if not values:
        return Decimal('0')
    
    decimal_values = [safe_decimal(v) for v in values]
    return min(decimal_values)


def calculate_max(values):
    """최댓값 계산"""
    if not values:
        return Decimal('0')
    
    decimal_values = [safe_decimal(v) for v in values]
    return max(decimal_values)


def calculate_tax(amount, tax_rate=Decimal('0.1')):
    """세금 계산 (기본 10%)"""
    amount_decimal = safe_decimal(amount)
    tax = amount_decimal * safe_decimal(tax_rate)
    return round_decimal(tax, 0)


def calculate_discount(original_price, discount_rate):
    """할인 가격 계산"""
    original = safe_decimal(original_price)
    rate = safe_decimal(discount_rate)
    
    if rate >= 1:
        # 할인율이 1 이상이면 퍼센트로 간주
        rate = rate / 100
    
    discount_amount = original * rate
    final_price = original - discount_amount
    
    return {
        'original_price': original,
        'discount_rate': rate * 100,
        'discount_amount': round_decimal(discount_amount, 0),
        'final_price': round_decimal(final_price, 0)
    }


def format_number_korean(value):
    """한국식 숫자 표기 (만, 억 단위)"""
    decimal_value = safe_decimal(value)
    
    if decimal_value >= 100000000:  # 억
        billions = decimal_value / 100000000
        return f"{billions:.1f}억"
    elif decimal_value >= 10000:  # 만
        ten_thousands = decimal_value / 10000
        return f"{ten_thousands:.1f}만"
    else:
        return f"{int(decimal_value):,}"


def is_zero(value, precision=Decimal('0.01')):
    """값이 0인지 확인 (오차 범위 고려)"""
    decimal_value = safe_decimal(value)
    return abs(decimal_value) < precision


def compare_decimals(value1, value2, precision=Decimal('0.01')):
    """두 Decimal 값 비교 (오차 범위 고려)"""
    diff = abs(safe_decimal(value1) - safe_decimal(value2))
    return diff < precision