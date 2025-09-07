#!/usr/bin/env python3
"""
PWA 아이콘 생성 스크립트
SVG 로고로부터 여러 크기의 PNG 아이콘을 생성합니다.
"""

from PIL import Image, ImageDraw
import os

def create_icon(size, output_path):
    """그라데이션과 사각형 패턴으로 아이콘 생성"""
    
    # 새 이미지 생성
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # 배경: 그라데이션 효과를 위한 단순화된 색상
    # 실제 그라데이션은 PIL에서 복잡하므로 대표 색상 사용
    bg_color = (10, 132, 255, 255)  # #0A84FF
    draw.rounded_rectangle([(0, 0), (size, size)], 
                          radius=size//4, 
                          fill=bg_color)
    
    # 4개의 사각형 패턴
    rect_size = size // 4
    padding = size // 8
    positions = [
        (padding, padding),  # 좌상
        (size//2 + padding//2, padding),  # 우상
        (padding, size//2 + padding//2),  # 좌하
        (size//2 + padding//2, size//2 + padding//2)  # 우하
    ]
    
    opacities = [230, 178, 178, 127]  # 90%, 70%, 70%, 50%
    
    for i, (x, y) in enumerate(positions):
        white_with_opacity = (255, 255, 255, opacities[i])
        
        # 작은 둥근 사각형 그리기
        corner_radius = rect_size // 8
        
        # 사각형을 그리기 위한 임시 이미지
        rect_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        rect_draw = ImageDraw.Draw(rect_img)
        rect_draw.rounded_rectangle(
            [(x, y), (x + rect_size, y + rect_size)],
            radius=corner_radius,
            fill=white_with_opacity
        )
        
        # 메인 이미지에 합성
        img = Image.alpha_composite(img, rect_img)
    
    # 저장
    img.save(output_path, 'PNG')
    print(f"Generated: {output_path}")

def main():
    """모든 크기의 아이콘 생성"""
    
    # 아이콘 크기 목록
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    
    # 출력 디렉토리
    output_dir = '/home/user/onesquare/src/static/images/icons'
    os.makedirs(output_dir, exist_ok=True)
    
    # 각 크기별로 아이콘 생성
    for size in sizes:
        output_path = os.path.join(output_dir, f'icon-{size}x{size}.png')
        create_icon(size, output_path)
    
    print(f"\n✅ 모든 아이콘 생성 완료!")
    print(f"   위치: {output_dir}")

if __name__ == '__main__':
    main()