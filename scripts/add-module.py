#!/usr/bin/env python3
"""
OneSquare 모듈 추가 CLI 도구
MODULE_TRACKER.md에 새 모듈을 쉽게 추가하는 스크립트
"""

import sys
import os
from datetime import datetime
from pathlib import Path
import re

class ModuleAdder:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.tracker_path = self.project_root / "MODULE_TRACKER.md"
        self.categories = {
            '1': 'Core Modules',
            '2': 'Utils Modules', 
            '3': 'Feature Modules',
            '4': 'Integration Modules'
        }
        self.status_icons = {
            '1': ('⏸️ 대기', 'pending'),
            '2': ('🔄 개발중', 'in_progress'),
            '3': ('✅ 완료', 'completed')
        }
        
    def print_header(self):
        """헤더 출력"""
        print("\n" + "="*50)
        print("🚀 OneSquare 모듈 추가 도구")
        print("="*50 + "\n")
        
    def get_input(self, prompt, default=None, required=True):
        """사용자 입력 받기"""
        if default:
            prompt = f"{prompt} [{default}]: "
        else:
            prompt = f"{prompt}: "
            
        value = input(prompt).strip()
        
        if not value and default:
            return default
        elif not value and required:
            print("❌ 필수 입력 항목입니다.")
            return self.get_input(prompt.rstrip(": "), default, required)
        
        return value
    
    def select_category(self):
        """카테고리 선택"""
        print("\n📂 카테고리 선택:")
        print("1. Core Modules (설정 파일)")
        print("2. Utils Modules (유틸리티)")
        print("3. Feature Modules (기능 앱)")
        print("4. Integration Modules (통합)")
        
        choice = self.get_input("선택 (1-4)", "3")
        if choice not in self.categories:
            print("❌ 잘못된 선택입니다.")
            return self.select_category()
        
        return self.categories[choice]
    
    def select_status(self):
        """상태 선택"""
        print("\n📊 모듈 상태:")
        print("1. ⏸️ 대기")
        print("2. 🔄 개발중")
        print("3. ✅ 완료")
        
        choice = self.get_input("선택 (1-3)", "2")
        if choice not in self.status_icons:
            print("❌ 잘못된 선택입니다.")
            return self.select_status()
        
        return self.status_icons[choice][0]
    
    def collect_module_info(self):
        """모듈 정보 수집"""
        self.print_header()
        
        # 기본 정보
        print("📝 모듈 정보 입력\n")
        module_name = self.get_input("모듈명 (예: auth_helper.py)")
        
        # 파일 경로 자동 제안
        if '.py' in module_name:
            suggested_path = f"/src/apps/{module_name.split('.')[0]}/{module_name}"
        else:
            suggested_path = f"/src/apps/{module_name}/"
        
        file_path = self.get_input("파일 경로", suggested_path)
        
        # 카테고리 및 상태
        category = self.select_category()
        status = self.select_status()
        
        # 의존성 및 이유
        dependencies = self.get_input("의존성 (쉼표 구분, 없으면 '-')", "-")
        reason = self.get_input("추가 이유")
        
        # 날짜
        add_date = datetime.now().strftime("%Y-%m-%d")
        
        return {
            'name': module_name,
            'path': file_path,
            'category': category,
            'status': status,
            'dependencies': dependencies,
            'reason': reason,
            'date': add_date
        }
    
    def add_to_tracker(self, module_info):
        """MODULE_TRACKER.md에 추가"""
        with open(self.tracker_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 카테고리 섹션 찾기
        category_pattern = f"### .*{module_info['category']}"
        match = re.search(category_pattern, content)
        
        if not match:
            print(f"❌ 카테고리 '{module_info['category']}'를 찾을 수 없습니다.")
            return False
        
        # 테이블 끝 찾기
        start = match.end()
        table_end = content.find("\n### ", start)
        if table_end == -1:
            table_end = content.find("\n---", start)
        
        # 새 행 생성
        new_row = f"| **{module_info['name']}** | `{module_info['path']}` | {module_info['status']} | {module_info['dependencies']} | {module_info['reason']} | {module_info['date']} |\n"
        
        # 적절한 위치에 삽입
        insert_pos = content.rfind("\n", start, table_end)
        new_content = content[:insert_pos] + "\n" + new_row + content[insert_pos+1:]
        
        # 파일 저장
        with open(self.tracker_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
    
    def update_architecture(self):
        """아키텍처 다이어그램 업데이트"""
        print("\n🔄 아키텍처 다이어그램 업데이트 중...")
        os.system("python3 scripts/update-architecture.py")
        
    def show_summary(self, module_info):
        """요약 출력"""
        print("\n" + "="*50)
        print("✅ 모듈 추가 완료!")
        print("="*50)
        print(f"📦 모듈명: {module_info['name']}")
        print(f"📁 경로: {module_info['path']}")
        print(f"📂 카테고리: {module_info['category']}")
        print(f"📊 상태: {module_info['status']}")
        print(f"🔗 의존성: {module_info['dependencies']}")
        print(f"📝 이유: {module_info['reason']}")
        print(f"📅 추가일: {module_info['date']}")
        print("="*50)
        
    def quick_add(self):
        """빠른 추가 모드"""
        print("\n⚡ 빠른 모듈 추가 (Enter로 기본값 사용)")
        
        # 최소 정보만 입력
        module_name = self.get_input("모듈명")
        category_num = self.get_input("카테고리 (1:Core 2:Utils 3:Feature 4:Integration)", "3")
        status_num = self.get_input("상태 (1:대기 2:개발중 3:완료)", "2")
        
        # 자동 생성
        if '.py' in module_name:
            app_name = module_name.split('.')[0].replace('_', '')
            file_path = f"/src/apps/{app_name}/{module_name}"
        else:
            file_path = f"/src/apps/{module_name}/"
        
        module_info = {
            'name': module_name,
            'path': file_path,
            'category': self.categories.get(category_num, 'Feature Modules'),
            'status': self.status_icons.get(status_num, ('🔄 개발중', 'in_progress'))[0],
            'dependencies': '-',
            'reason': '새 기능 구현',
            'date': datetime.now().strftime("%Y-%m-%d")
        }
        
        return module_info
    
    def run(self):
        """메인 실행"""
        try:
            # 모드 선택
            print("\n모드 선택:")
            print("1. 상세 입력 모드")
            print("2. 빠른 추가 모드 (기본값 사용)")
            mode = self.get_input("선택 (1-2)", "2")
            
            if mode == "1":
                module_info = self.collect_module_info()
            else:
                module_info = self.quick_add()
            
            # MODULE_TRACKER.md에 추가
            if self.add_to_tracker(module_info):
                self.show_summary(module_info)
                
                # 다이어그램 업데이트 확인
                update = self.get_input("\n다이어그램을 업데이트하시겠습니까? (y/n)", "y")
                if update.lower() == 'y':
                    self.update_architecture()
                    print("✨ 모든 작업이 완료되었습니다!")
            else:
                print("❌ 모듈 추가 실패")
                
        except KeyboardInterrupt:
            print("\n\n👋 취소되었습니다.")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            sys.exit(1)

def main():
    """진입점"""
    adder = ModuleAdder()
    adder.run()

if __name__ == "__main__":
    main()