import random

# Predefined special cases to enhance test coverage
interesting_str = [
    '''"a" + String.fromCharCode(0x4141)''',
    '''"\\\\xfe\\\\xff"''',
    '''"https://invalid.noexist.com/abc"'''
]

def generate_code_point():
    """Generate valid Unicode code points (0x0 to 0x10FFFF)"""
    r = random.random()
    if r < 0.7:  # 70% probability for Basic Multilingual Plane (BMP)
        # Exclude surrogate range (0xD800-0xDFFF)
        return random.choice([
            random.randint(0x0000, 0xD7FF),
            random.randint(0xE000, 0xFFFF)
        ])
    elif r < 0.95:  # 25% probability for Supplementary Planes
        return random.randint(0x10000, 0x10FFFF)
    else:  # 5% probability for control characters
        return random.choice([random.randint(0x0, 0x1F), 0x7F])

def escape_code_point(code_point):
    """Generate JavaScript escape sequences"""
    
    # Hexadecimal escapes
    if code_point <= 0xFF and random.random() < 0.3:
        return '\\\\x%02x' % code_point
    
    # Handle supplementary characters with surrogate pairs
    if code_point > 0xFFFF:
        # Always use surrogate pairs
        shifted = code_point - 0x10000
        high = 0xD800 + (shifted >> 10)
        low = 0xDC00 + (shifted & 0x3FF)
        return '\\\\u%04x\\\\u%04x' % (high, low)
    
    # Standard 4-digit Unicode escapes
    return '\\\\u%04x' % code_point

def generate_literal():
    """Generate string literals"""
    length = int(abs(random.gauss(8, 10)))
    length = max(0, min(length, 2000))
    
    chars = []
    for _ in range(length):
        cp = generate_code_point()
        
        # Mandatory escaping cases
        if cp in (0x22, 0x5C) or (0x00 <= cp <= 0x1F):
            chars.append(escape_code_point(cp))
            continue
            
        # 30% probability to force escaping
        if random.random() < 0.3:
            chars.append(escape_code_point(cp))
            continue
            
        # Try direct character representation
        try:
            c = chr(cp)
            if 0x20 <= cp <= 0x7E and cp not in (0x22, 0x5C):
                chars.append(c)
            else:
                chars.append(escape_code_point(cp))
        except:
            chars.append(escape_code_point(cp))

    # 10% probability to add BOM
    if random.random() < 0.1:
        chars.insert(0, '\\\\xfe\\\\xff')
    if random.random() < 0.1:
        chars.append('\\\\xff\\\\xfe')

    return '"%s"' % ''.join(chars)


def generate_dynamic():
    """Generate dynamic construction expressions"""
    parts = []
    for _ in range(random.randint(1, 5)):
        if random.random() < 0.5:
            parts.append(generate_literal())
        else:
            cp = generate_code_point()
            # method = 'String.fromCodePoint' if cp > 0xFFFF else 'String.fromCharCode'
            method = 'String.fromCharCode'
            parts.append(f'{method}(0x{cp:x})')
    
    if random.random() < 0.5:
        return 'String(%s)' % ' + '.join(parts)
    return ' + '.join(parts)

def generate_special_string():
    """Generate special string constructions"""
    choices = [
        lambda: 'Array(%d).join(%s)' % (random.randint(1, 10000), generate_literal()),
        lambda: 'new ArrayBuffer(%d)' % random.randint(0, 1024),
        lambda: '"%s"' % escape_code_point(generate_code_point()),
        lambda: '"\\\\x%02x\\\\x%02x"' % (random.randint(0,0xff), random.randint(0,0xff))
    ]
    return random.choice(choices)()

def rand_str():
    """Main entry function"""
    # 10% probability to use predefined special cases
    if random.random() < 0.1:
        return random.choice(interesting_str)
    
    # Mode selection
    r = random.random()
    if r < 0.45:  # 45% probability for literals
        return generate_literal()
    elif r < 0.75:  # 30% probability for dynamic expressions
        return generate_dynamic()
    else:  # 25% probability for special constructions
        return generate_special_string()
    

def rand_num():
    """Generate high-quality random numeric strings for JavaScript engine testing"""
    choices = [
        ('integer', 20),       # Basic integers
        ('float', 15),         # Floating point numbers
        ('scientific', 15),    # Scientific notation
        ('hex', 15),           # Hexadecimal values
        ('special', 5),        # Special values (Infinity/NaN)
        ('huge', 15),          # Extremely large numbers
        ('edge_case', 15),     # JavaScript-specific edge cases
    ]
    types, weights = zip(*choices)
    selected_type = random.choices(types, weights=weights, k=1)[0]

    # Dispatch to corresponding generator based on selected type
    if selected_type == 'integer':
        return generate_integer()
    elif selected_type == 'float':
        return generate_float()
    elif selected_type == 'scientific':
        return generate_scientific()
    elif selected_type == 'hex':
        return generate_hex()
    elif selected_type == 'special':
        return generate_special_number()
    elif selected_type == 'huge':
        return generate_huge()
    elif selected_type == 'edge_case':
        return generate_edge_case()

def generate_integer():
    """Generate integers with various characteristics"""
    sign = '-' if random.random() < 0.3 else ''
    parts = random.choices(
        ['zero', 'small', 'medium', 'large'],
        weights=[0.1, 0.4, 0.3, 0.2],  # Probability distribution
        k=1
    )[0]
    
    if parts == 'zero':
        num = '0'
    elif parts == 'small':
        num = str(random.randint(0, 255))  # Byte-sized values
    elif parts == 'medium':
        num = str(random.randint(256, 0xFFFF))  # Common word sizes
    else:
        num = str(random.randint(0x10000, 0x7FFFFFFF))  # Large 32-bit values

    return sign + num

def generate_float():
    """Generate floating-point numbers with different formats"""
    sign = '-' if random.random() < 0.3 else ''
    structure = random.choice(['int.frac', '.frac'])  # Different float formats
    
    int_part = ''
    if 'int' in structure:
        int_part = generate_integer().lstrip('-')
    
    frac_part = ''
    if 'frac' in structure:
        frac_part = ''.join(random.choices('0123456789', k=random.randint(1, 6)))
        # Add trailing zeros with 30% probability
        if random.random() < 0.3:
            frac_part += '0' * random.randint(1, 3)
    
    return f"{sign}{int_part}.{frac_part}" if structure == 'int.frac' else \
           f"{sign}.{frac_part}"

def generate_scientific():
    """Generate numbers in scientific notation"""
    mantissa = generate_float() if random.random() < 0.5 else generate_integer()
    e_char = random.choice(['e', 'E'])  # Both lowercase and uppercase
    exp_sign = random.choice(['+', '-', ''])  # Optional exponent sign
    exp = str(random.randint(0, 308))     # Exponent range matching JS limits
    return f"{mantissa}{e_char}{exp_sign}{exp}"

def generate_hex():
    """Generate hexadecimal values"""
    prefix = random.choice(['0x', '0X'])  # Case variations
    digits = ''.join(random.choices('0123456789abcdefABCDEF', k=random.randint(1, 8)))
    return prefix + digits

def generate_special_number():
    """Generate special numeric values"""
    return random.choice(['Infinity', '-Infinity', 'NaN'])

def generate_huge():
    """Generate extremely large numbers for stress testing"""
    sign = '-' if random.random() < 0.3 else ''
    num_length = random.randint(20, 30)
    first_digit = random.choice('123456789')
    rest_digits = ''.join(random.choices('0123456789', k=num_length-1))
    return f"{sign}{first_digit}{rest_digits}"

def generate_edge_case():
    """Generate JavaScript-specific edge cases"""
    cases = [
        '0', '-0', '-1', '0x7fffffff', '0xffffffff', 
        '9007199254740991',  # MAX_SAFE_INTEGER
        '9007199254740992',  # MAX_SAFE_INTEGER + 1
        '1.7976931348623157e+308',  # MAX_VALUE
        '5e-324',            # MIN_VALUE
        '0.000000000000000000001',
        '123456789012345678901234567890',
        '0xdeadbeef'
    ]
    return random.choice(cases)