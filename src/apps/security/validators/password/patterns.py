"""
Common password patterns
일반적인 비밀번호 패턴
"""

# 일반적인 비밀번호 패턴 정규식
COMMON_PASSWORD_PATTERNS = [
    # 단순 반복 패턴
    r'^(.)\1+$',  # aaaa, 1111 등
    r'^(..)\1+$',  # abab, 1212 등
    r'^(...)\1+$',  # abcabc, 123123 등
    
    # 키보드 패턴
    r'^qwerty',
    r'^asdf',
    r'^zxcv',
    r'^qazwsx',
    r'^1qaz2wsx',
    
    # 날짜 패턴
    r'^\d{4}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])$',  # YYYYMMDD
    r'^(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{4}$',  # MMDDYYYY
    r'^(19|20)\d{2}$',  # 연도만
    
    # 일반적인 단어 + 숫자
    r'^password\d+$',
    r'^admin\d+$',
    r'^user\d+$',
    r'^test\d+$',
    r'^demo\d+$',
    
    # 간단한 패턴
    r'^[a-z]+\d{1,4}$',  # 소문자+숫자
    r'^[A-Z]+\d{1,4}$',  # 대문자+숫자
    r'^\d+[a-z]+$',  # 숫자+소문자
    
    # 계절 관련
    r'^(spring|summer|fall|autumn|winter)\d*',
    r'^(january|february|march|april|may|june|july|august|september|october|november|december)\d*',
    
    # 흔한 이름 패턴
    r'^(john|jane|mike|david|sarah|mary|james|robert|jennifer|michael)\d*',
    
    # 한국어 로마자 패턴
    r'^(samsung|hyundai|korea|seoul|busan)\d*',
]

# 금지된 비밀번호 목록
BLACKLISTED_PASSWORDS = [
    'password', 'Password', 'PASSWORD',
    '12345678', '123456789', '1234567890',
    'qwerty', 'QWERTY', 'Qwerty',
    'admin', 'Admin', 'ADMIN',
    'user', 'User', 'USER',
    'test', 'Test', 'TEST',
    'demo', 'Demo', 'DEMO',
    'welcome', 'Welcome', 'WELCOME',
    'changeme', 'ChangeMe', 'CHANGEME',
    'letmein', 'LetMeIn', 'LETMEIN',
    'master', 'Master', 'MASTER',
    'monkey', 'Monkey', 'MONKEY',
    'dragon', 'Dragon', 'DRAGON',
    'baseball', 'Baseball', 'BASEBALL',
    'football', 'Football', 'FOOTBALL',
    'iloveyou', 'ILoveYou', 'ILOVEYOU',
    'sunshine', 'Sunshine', 'SUNSHINE',
    'princess', 'Princess', 'PRINCESS',
    'trustno1', 'TrustNo1', 'TRUSTNO1',
]

def is_blacklisted(password):
    """비밀번호가 블랙리스트에 있는지 확인"""
    return password in BLACKLISTED_PASSWORDS or password.lower() in [p.lower() for p in BLACKLISTED_PASSWORDS]