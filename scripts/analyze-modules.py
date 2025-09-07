#!/usr/bin/env python3
"""
OneSquare 모듈 분석 도구
모듈 간 중복, 복잡도, 의존성을 분석하고 리팩토링 제안
"""

import os
import ast
import re
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
import difflib

class ModuleAnalyzer:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.src_path = self.project_root / "src"
        self.apps_path = self.src_path / "apps"
        self.analysis_results = {
            'similar_modules': [],
            'duplicate_dependencies': {},
            'complexity_scores': {},
            'refactoring_suggestions': [],
            'statistics': {}
        }
        
    def print_header(self):
        """헤더 출력"""
        print("\n" + "="*60)
        print("🔍 OneSquare 모듈 분석 도구")
        print("="*60)
        
    def analyze_python_file(self, file_path):
        """Python 파일 분석"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
                
            return {
                'path': str(file_path),
                'content': content,
                'tree': tree,
                'imports': self.extract_imports(tree),
                'classes': self.extract_classes(tree),
                'functions': self.extract_functions(tree),
                'complexity': self.calculate_complexity(tree),
                'lines': len(content.splitlines()),
                'docstrings': self.extract_docstrings(tree)
            }
        except Exception as e:
            return None
            
    def extract_imports(self, tree):
        """import 문 추출"""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)
        return imports
        
    def extract_classes(self, tree):
        """클래스 정보 추출"""
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                classes.append({
                    'name': node.name,
                    'methods': methods,
                    'lines': node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 0
                })
        return classes
        
    def extract_functions(self, tree):
        """함수 정보 추출"""
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and not isinstance(node, ast.AsyncFunctionDef):
                # 클래스 메서드가 아닌 경우만
                parent = self.get_parent_class(tree, node)
                if not parent:
                    functions.append({
                        'name': node.name,
                        'args': len(node.args.args),
                        'lines': node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 0
                    })
        return functions
        
    def get_parent_class(self, tree, node):
        """노드의 부모 클래스 찾기"""
        for cls in ast.walk(tree):
            if isinstance(cls, ast.ClassDef):
                for item in cls.body:
                    if item == node:
                        return cls
        return None
        
    def calculate_complexity(self, tree):
        """Cyclomatic Complexity 계산"""
        complexity = 1  # 기본 복잡도
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
                
        return complexity
        
    def extract_docstrings(self, tree):
        """docstring 추출"""
        docstrings = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                docstring = ast.get_docstring(node)
                if docstring:
                    docstrings.append(docstring[:100])  # 처음 100자만
        return docstrings
        
    def find_similar_modules(self, modules):
        """비슷한 모듈 찾기"""
        print("\n📊 비슷한 기능의 모듈 감지 중...")
        similar_pairs = []
        
        for i, mod1 in enumerate(modules):
            for mod2 in modules[i+1:]:
                # 함수/클래스 이름 비교
                funcs1 = set([f['name'] for f in mod1.get('functions', [])])
                funcs2 = set([f['name'] for f in mod2.get('functions', [])])
                classes1 = set([c['name'] for c in mod1.get('classes', [])])
                classes2 = set([c['name'] for c in mod2.get('classes', [])])
                
                # 유사도 계산
                func_similarity = len(funcs1 & funcs2) / max(len(funcs1 | funcs2), 1)
                class_similarity = len(classes1 & classes2) / max(len(classes1 | classes2), 1)
                
                # 코드 유사도 (간단한 버전)
                if mod1.get('content') and mod2.get('content'):
                    seq = difflib.SequenceMatcher(None, 
                                                 mod1['content'][:1000], 
                                                 mod2['content'][:1000])
                    content_similarity = seq.ratio()
                else:
                    content_similarity = 0
                    
                total_similarity = (func_similarity + class_similarity + content_similarity) / 3
                
                if total_similarity > 0.3:  # 30% 이상 유사
                    similar_pairs.append({
                        'module1': Path(mod1['path']).name,
                        'module2': Path(mod2['path']).name,
                        'similarity': round(total_similarity * 100, 1),
                        'shared_functions': list(funcs1 & funcs2),
                        'shared_classes': list(classes1 & classes2)
                    })
                    
        return similar_pairs
        
    def find_duplicate_dependencies(self, modules):
        """중복 의존성 찾기"""
        print("\n🔗 중복 의존성 분석 중...")
        
        # 모든 import 수집
        import_counter = Counter()
        module_imports = defaultdict(list)
        
        for mod in modules:
            if mod and 'imports' in mod:
                mod_name = Path(mod['path']).stem
                for imp in mod['imports']:
                    import_counter[imp] += 1
                    module_imports[imp].append(mod_name)
                    
        # 2개 이상의 모듈에서 사용하는 import
        duplicates = {}
        for imp, count in import_counter.items():
            if count >= 2 and not imp.startswith('django'):  # Django 기본 제외
                duplicates[imp] = {
                    'count': count,
                    'modules': module_imports[imp]
                }
                
        return duplicates
        
    def analyze_complexity(self, modules):
        """모듈 복잡도 분석"""
        print("\n📈 모듈 복잡도 분석 중...")
        
        complexity_data = {}
        
        for mod in modules:
            if mod:
                mod_name = Path(mod['path']).stem
                
                # 복잡도 점수 계산
                score = 0
                details = []
                
                # Cyclomatic Complexity
                cc = mod.get('complexity', 0)
                if cc > 10:
                    score += (cc - 10) * 2
                    details.append(f"높은 순환 복잡도: {cc}")
                    
                # 파일 길이
                lines = mod.get('lines', 0)
                if lines > 200:
                    score += (lines - 200) / 50
                    details.append(f"긴 파일: {lines}줄")
                    
                # 클래스/함수 수
                num_classes = len(mod.get('classes', []))
                num_functions = len(mod.get('functions', []))
                
                if num_classes > 3:
                    score += (num_classes - 3) * 3
                    details.append(f"많은 클래스: {num_classes}개")
                    
                if num_functions > 10:
                    score += (num_functions - 10)
                    details.append(f"많은 함수: {num_functions}개")
                    
                # Docstring 부족
                if not mod.get('docstrings'):
                    score += 5
                    details.append("문서화 부족")
                    
                complexity_data[mod_name] = {
                    'score': round(score, 1),
                    'level': self.get_complexity_level(score),
                    'details': details,
                    'metrics': {
                        'cyclomatic': cc,
                        'lines': lines,
                        'classes': num_classes,
                        'functions': num_functions,
                        'imports': len(mod.get('imports', []))
                    }
                }
                
        return complexity_data
        
    def get_complexity_level(self, score):
        """복잡도 레벨 결정"""
        if score < 5:
            return "낮음 🟢"
        elif score < 15:
            return "보통 🟡"
        elif score < 30:
            return "높음 🟠"
        else:
            return "매우 높음 🔴"
            
    def generate_refactoring_suggestions(self):
        """리팩토링 제안 생성"""
        suggestions = []
        
        # 비슷한 모듈 병합 제안
        if self.analysis_results['similar_modules']:
            for similar in self.analysis_results['similar_modules']:
                if similar['similarity'] > 50:
                    suggestions.append({
                        'type': '모듈 병합',
                        'priority': '높음',
                        'modules': [similar['module1'], similar['module2']],
                        'reason': f"{similar['similarity']}% 유사도",
                        'action': f"{similar['module1']}과 {similar['module2']}를 하나의 모듈로 통합 검토"
                    })
                    
        # 복잡도 기반 제안
        for mod_name, complexity in self.analysis_results['complexity_scores'].items():
            if complexity['score'] > 20:
                suggestions.append({
                    'type': '모듈 분할',
                    'priority': '높음' if complexity['score'] > 30 else '중간',
                    'modules': [mod_name],
                    'reason': f"복잡도 점수 {complexity['score']}",
                    'action': f"{mod_name} 모듈을 작은 단위로 분할"
                })
                
        # 중복 의존성 제안
        for dep, info in self.analysis_results['duplicate_dependencies'].items():
            if info['count'] >= 3:
                suggestions.append({
                    'type': '공통 모듈화',
                    'priority': '중간',
                    'modules': info['modules'],
                    'reason': f"{dep}를 {info['count']}개 모듈에서 사용",
                    'action': f"{dep} 관련 기능을 공통 유틸리티로 추출"
                })
                
        return suggestions
        
    def generate_report(self):
        """분석 리포트 생성"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = []
        report.append("\n" + "="*60)
        report.append("📊 OneSquare 모듈 분석 리포트")
        report.append(f"📅 생성 시간: {timestamp}")
        report.append("="*60)
        
        # 1. 통계
        report.append("\n## 📈 전체 통계")
        report.append(f"- 분석된 모듈: {self.analysis_results['statistics'].get('total_modules', 0)}개")
        report.append(f"- 총 코드 라인: {self.analysis_results['statistics'].get('total_lines', 0):,}줄")
        report.append(f"- 평균 복잡도: {self.analysis_results['statistics'].get('avg_complexity', 0):.1f}")
        
        # 2. 비슷한 모듈
        if self.analysis_results['similar_modules']:
            report.append("\n## 🔄 비슷한 모듈")
            for similar in sorted(self.analysis_results['similar_modules'], 
                                 key=lambda x: x['similarity'], reverse=True)[:5]:
                report.append(f"- {similar['module1']} ↔ {similar['module2']}: "
                            f"{similar['similarity']}% 유사")
                if similar['shared_functions']:
                    report.append(f"  공통 함수: {', '.join(similar['shared_functions'][:3])}")
                    
        # 3. 복잡도 높은 모듈
        report.append("\n## 🔴 복잡도 높은 모듈 (상위 5개)")
        complex_modules = sorted(self.analysis_results['complexity_scores'].items(),
                                key=lambda x: x[1]['score'], reverse=True)[:5]
        for mod_name, complexity in complex_modules:
            report.append(f"- {mod_name}: {complexity['level']} (점수: {complexity['score']})")
            for detail in complexity['details'][:2]:
                report.append(f"  • {detail}")
                
        # 4. 중복 의존성
        if self.analysis_results['duplicate_dependencies']:
            report.append("\n## 🔗 중복 의존성 (상위 5개)")
            sorted_deps = sorted(self.analysis_results['duplicate_dependencies'].items(),
                               key=lambda x: x[1]['count'], reverse=True)[:5]
            for dep, info in sorted_deps:
                report.append(f"- {dep}: {info['count']}개 모듈에서 사용")
                report.append(f"  사용 모듈: {', '.join(info['modules'][:4])}")
                
        # 5. 리팩토링 제안
        report.append("\n## 💡 리팩토링 제안")
        suggestions = self.generate_refactoring_suggestions()
        self.analysis_results['refactoring_suggestions'] = suggestions
        
        high_priority = [s for s in suggestions if s['priority'] == '높음']
        medium_priority = [s for s in suggestions if s['priority'] == '중간']
        
        if high_priority:
            report.append("\n### 🔴 높은 우선순위")
            for sug in high_priority[:3]:
                report.append(f"- [{sug['type']}] {sug['action']}")
                report.append(f"  이유: {sug['reason']}")
                
        if medium_priority:
            report.append("\n### 🟡 중간 우선순위")
            for sug in medium_priority[:3]:
                report.append(f"- [{sug['type']}] {sug['action']}")
                report.append(f"  이유: {sug['reason']}")
                
        # 6. 건강도 점수
        health_score = self.calculate_health_score()
        report.append(f"\n## 🏥 전체 모듈 건강도: {health_score}/100")
        
        if health_score >= 80:
            report.append("✅ 우수한 상태입니다!")
        elif health_score >= 60:
            report.append("🟡 개선이 필요한 부분이 있습니다.")
        else:
            report.append("🔴 리팩토링이 시급합니다.")
            
        report.append("\n" + "="*60)
        
        return '\n'.join(report)
        
    def calculate_health_score(self):
        """전체 건강도 점수 계산"""
        score = 100
        
        # 비슷한 모듈 감점
        similar_count = len(self.analysis_results['similar_modules'])
        score -= min(similar_count * 3, 20)
        
        # 높은 복잡도 감점
        high_complexity = sum(1 for _, c in self.analysis_results['complexity_scores'].items()
                            if c['score'] > 20)
        score -= min(high_complexity * 5, 30)
        
        # 중복 의존성 감점
        dup_deps = len(self.analysis_results['duplicate_dependencies'])
        score -= min(dup_deps * 2, 20)
        
        return max(score, 0)
        
    def save_report(self, report):
        """리포트 저장"""
        report_dir = self.project_root / "docs" / "analysis"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"module_analysis_{timestamp}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
            
        # JSON 형식으로도 저장
        json_file = report_dir / f"module_analysis_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_results, f, ensure_ascii=False, indent=2, default=str)
            
        return report_file, json_file
        
    def run(self):
        """메인 실행"""
        self.print_header()
        
        # 모든 Python 파일 수집
        print("\n📂 Python 모듈 수집 중...")
        python_files = list(self.apps_path.rglob("*.py"))
        
        # __pycache__ 및 migrations 제외
        python_files = [f for f in python_files 
                       if '__pycache__' not in str(f) 
                       and 'migrations' not in str(f)
                       and '__init__.py' not in f.name]
        
        print(f"  {len(python_files)}개 파일 발견")
        
        # 각 파일 분석
        print("\n🔍 모듈 분석 중...")
        modules = []
        total_lines = 0
        total_complexity = 0
        
        for file_path in python_files:
            module = self.analyze_python_file(file_path)
            if module:
                modules.append(module)
                total_lines += module.get('lines', 0)
                total_complexity += module.get('complexity', 0)
                print(f"  ✓ {file_path.name}")
                
        # 통계 저장
        self.analysis_results['statistics'] = {
            'total_modules': len(modules),
            'total_lines': total_lines,
            'avg_complexity': total_complexity / max(len(modules), 1)
        }
        
        # 분석 수행
        self.analysis_results['similar_modules'] = self.find_similar_modules(modules)
        self.analysis_results['duplicate_dependencies'] = self.find_duplicate_dependencies(modules)
        self.analysis_results['complexity_scores'] = self.analyze_complexity(modules)
        
        # 리포트 생성
        report = self.generate_report()
        
        # 리포트 출력
        print(report)
        
        # 리포트 저장
        md_file, json_file = self.save_report(report)
        print(f"\n📄 리포트 저장됨:")
        print(f"  - Markdown: {md_file}")
        print(f"  - JSON: {json_file}")
        
        print("\n✨ 분석 완료!")

def main():
    """진입점"""
    analyzer = ModuleAnalyzer()
    analyzer.run()

if __name__ == "__main__":
    main()