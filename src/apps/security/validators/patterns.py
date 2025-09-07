"""보안 검증을 위한 패턴 정의"""

# XSS 위험 패턴
XSS_PATTERNS = [
    r'<script[^>]*>.*?</script>',
    r'javascript:',
    r'on\w+\s*=',
    r'<iframe[^>]*>',
    r'<object[^>]*>',
    r'<embed[^>]*>',
    r'<link[^>]*>',
    r'<meta[^>]*>',
    r'<style[^>]*>.*?</style>',
    r'vbscript:',
    r'data:text/html',
    r'expression\s*\(',
    r'@import',
]

# SQL Injection 위험 패턴
SQL_INJECTION_PATTERNS = [
    r'(union|select|insert|update|delete|drop|create|alter|exec|execute)\s+',
    r';\s*(union|select|insert|update|delete|drop|create|alter|exec|execute)\s+',
    r'--\s*$',
    r'/\*.*?\*/',
    r"'\s*(or|and)\s+",
    r'"\s*(or|and)\s+',
    r'(or|and)\s+\d+\s*=\s*\d+',
    r'(or|and)\s+\w+\s*(=|like)\s*',
    r'having\s+\d+=\d+',
    r'group\s+by\s+',
    r'order\s+by\s+',
]

# 위험한 파일 확장자
DANGEROUS_EXTENSIONS = [
    'exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js', 'jar',
    'php', 'asp', 'aspx', 'jsp', 'pl', 'py', 'rb', 'sh', 'ps1'
]

# 일반적인 패스워드 패턴
COMMON_PASSWORD_PATTERNS = [
    r'^password.*',
    r'^123.*',
    r'^qwerty.*',
    r'^admin.*',
    r'^letmein.*',
    r'^welcome.*',
    r'^.*123$',
    r'^.*password$',
]

# 위험한 URL 스키마
DANGEROUS_URL_SCHEMES = [
    'javascript:',
    'data:',
    'vbscript:',
    'file:',
    'about:',
    'chrome:',
]

# 파일명 위험 패턴
DANGEROUS_FILENAME_PATTERNS = [
    r'\.\./',  # 디렉토리 탐색
    r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])$',  # Windows 예약어
    r'[<>:"|?*]',  # 특수문자
    r'^\.',  # 숨김 파일
    r'\$',  # 특수 경로
]
