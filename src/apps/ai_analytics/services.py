"""
OneSquare AI 데이터 분석 서비스
매출 예측, 업무 효율성 분석, 성과 분석을 위한 AI 서비스 모듈
"""

import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple, Optional, Any
import statistics
import json
from django.db.models import Avg, Sum, Count, Q, F
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.revenue.models import RevenueRecord, Project, RevenueTarget
from apps.time_management.models import WorkTimeRecord
from .models import (
    AIModelConfig, RevenuePrediction, WorkEfficiencyAnalysis, 
    PerformanceAnalysis, AnomalyDetection, AIInsight
)

User = get_user_model()

class SimpleMLService:
    """간단한 머신러닝 서비스 (복잡한 외부 라이브러리 대신 기본 통계 활용)"""
    
    @staticmethod
    def linear_regression_forecast(data_points: List[float], periods: int = 3) -> Dict:
        """선형 회귀를 사용한 간단한 예측"""
        if len(data_points) < 2:
            return {'predictions': [data_points[-1] if data_points else 0] * periods, 'confidence': 0.5}
        
        n = len(data_points)
        x = list(range(n))
        y = data_points
        
        # 선형 회귀 계수 계산
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return {'predictions': [y_mean] * periods, 'confidence': 0.5}
        
        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        
        # 예측값 계산
        predictions = []
        for i in range(periods):
            next_x = n + i
            prediction = slope * next_x + intercept
            predictions.append(max(0, prediction))  # 음수 방지
        
        # 신뢰도 계산 (R²)
        y_pred = [slope * x[i] + intercept for i in range(n)]
        ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((y[i] - y_mean) ** 2 for i in range(n))
        
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.5
        confidence = max(0, min(1, r_squared))
        
        return {
            'predictions': predictions,
            'confidence': confidence,
            'slope': slope,
            'intercept': intercept
        }
    
    @staticmethod
    def moving_average_forecast(data_points: List[float], window: int = 3, periods: int = 3) -> Dict:
        """이동 평균을 사용한 예측"""
        if len(data_points) < window:
            avg_value = sum(data_points) / len(data_points) if data_points else 0
            return {'predictions': [avg_value] * periods, 'confidence': 0.6}
        
        # 이동 평균 계산
        moving_averages = []
        for i in range(window - 1, len(data_points)):
            ma = sum(data_points[i-window+1:i+1]) / window
            moving_averages.append(ma)
        
        # 최근 이동 평균으로 예측
        last_ma = moving_averages[-1]
        predictions = [last_ma] * periods
        
        # 트렌드 고려 (최근 3개 이동 평균의 변화율)
        if len(moving_averages) >= 3:
            recent_trend = (moving_averages[-1] - moving_averages[-3]) / 2
            for i in range(periods):
                predictions[i] = max(0, last_ma + recent_trend * (i + 1))
        
        # 변동성 기반 신뢰도
        if len(moving_averages) > 1:
            volatility = np.std(moving_averages)
            mean_value = np.mean(moving_averages)
            cv = volatility / mean_value if mean_value != 0 else 1
            confidence = max(0.3, min(0.9, 1 - cv))
        else:
            confidence = 0.6
        
        return {
            'predictions': predictions,
            'confidence': confidence,
            'trend': recent_trend if 'recent_trend' in locals() else 0
        }
    
    @staticmethod
    def detect_anomalies(data_points: List[float], threshold: float = 2.0) -> List[Dict]:
        """간단한 이상 탐지 (Z-score 기반)"""
        if len(data_points) < 3:
            return []
        
        mean = statistics.mean(data_points)
        stdev = statistics.stdev(data_points)
        
        anomalies = []
        for i, value in enumerate(data_points):
            if stdev > 0:
                z_score = abs(value - mean) / stdev
                if z_score > threshold:
                    anomalies.append({
                        'index': i,
                        'value': value,
                        'z_score': z_score,
                        'expected_range': (mean - threshold * stdev, mean + threshold * stdev),
                        'severity': 'high' if z_score > 3 else 'medium'
                    })
        
        return anomalies

class RevenuePredictionService:
    """매출 예측 서비스"""
    
    def __init__(self):
        self.ml_service = SimpleMLService()
    
    def create_monthly_prediction(self, months_ahead: int = 3, model_type: str = 'linear_regression') -> RevenuePrediction:
        """월별 매출 예측"""
        # 최근 12개월 매출 데이터 수집
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=365)
        
        monthly_revenues = self._get_monthly_revenue_data(start_date, end_date)
        
        # AI 모델 설정 가져오기 또는 생성
        model_config = self._get_or_create_model(model_type)
        
        # 예측 수행
        if model_type == 'linear_regression':
            forecast = self.ml_service.linear_regression_forecast(monthly_revenues, months_ahead)
        else:
            forecast = self.ml_service.moving_average_forecast(monthly_revenues, periods=months_ahead)
        
        # 예측 결과 저장
        prediction = RevenuePrediction.objects.create(
            model=model_config,
            prediction_type='monthly',
            prediction_date=end_date,
            target_period_start=end_date + timedelta(days=1),
            target_period_end=end_date + timedelta(days=30 * months_ahead),
            predicted_amount=Decimal(str(forecast['predictions'][0])),
            confidence_score=forecast['confidence'] * 100,
            factors_considered=[
                '과거 12개월 매출 데이터',
                '계절적 패턴',
                '트렌드 분석'
            ],
            trend_analysis=self._generate_trend_analysis(monthly_revenues, forecast),
            notes=f'{model_type} 모델을 사용한 {months_ahead}개월 예측'
        )
        
        # 신뢰구간 계산
        std_dev = np.std(monthly_revenues) if len(monthly_revenues) > 1 else 0
        margin = std_dev * 1.96  # 95% 신뢰구간
        
        prediction.lower_bound = max(0, prediction.predicted_amount - Decimal(str(margin)))
        prediction.upper_bound = prediction.predicted_amount + Decimal(str(margin))
        prediction.save()
        
        return prediction
    
    def create_project_prediction(self, project: Project) -> RevenuePrediction:
        """프로젝트별 매출 예측"""
        # 프로젝트 관련 데이터 수집
        project_revenues = list(
            project.revenue_records.filter(is_confirmed=True)
            .order_by('revenue_date')
            .values_list('net_amount', flat=True)
        )
        
        revenue_values = [float(r) for r in project_revenues]
        
        # 모델 설정
        model_config = self._get_or_create_model('project_forecast')
        
        # 남은 기간 계산
        remaining_days = (project.end_date - timezone.now().date()).days
        remaining_months = max(1, remaining_days // 30)
        
        # 예측 수행
        if len(revenue_values) >= 3:
            forecast = self.ml_service.linear_regression_forecast(revenue_values, 1)
            predicted_total = forecast['predictions'][0] * remaining_months
            confidence = forecast['confidence']
        else:
            # 계약 금액 기반 추정
            completed_revenue = sum(revenue_values)
            predicted_total = float(project.contract_amount) - completed_revenue
            confidence = 0.7
        
        prediction = RevenuePrediction.objects.create(
            model=model_config,
            prediction_type='project',
            prediction_date=timezone.now().date(),
            target_period_start=timezone.now().date(),
            target_period_end=project.end_date,
            predicted_amount=Decimal(str(max(0, predicted_total))),
            confidence_score=confidence * 100,
            factors_considered=[
                '프로젝트 기존 매출 패턴',
                '계약 금액',
                '진행률',
                '남은 기간'
            ],
            trend_analysis=f"프로젝트 진행률: {project.completion_rate:.1f}%",
            notes=f"프로젝트 '{project.name}' 완료까지 예상 매출"
        )
        
        return prediction
    
    def _get_monthly_revenue_data(self, start_date: date, end_date: date) -> List[float]:
        """월별 매출 데이터 조회"""
        monthly_data = []
        current_date = start_date.replace(day=1)
        
        while current_date <= end_date:
            next_month = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1)
            
            month_revenue = RevenueRecord.objects.filter(
                revenue_date__gte=current_date,
                revenue_date__lt=next_month,
                is_confirmed=True
            ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0')
            
            monthly_data.append(float(month_revenue))
            current_date = next_month
        
        return monthly_data
    
    def _get_or_create_model(self, model_type: str) -> AIModelConfig:
        """AI 모델 설정 가져오기 또는 생성"""
        model, created = AIModelConfig.objects.get_or_create(
            model_type=model_type,
            defaults={
                'name': f'{model_type.title()} 매출 예측 모델',
                'status': 'active',
                'description': f'{model_type} 알고리즘을 사용한 매출 예측',
                'parameters': {'default_periods': 3, 'confidence_threshold': 0.7}
            }
        )
        return model
    
    def _generate_trend_analysis(self, historical_data: List[float], forecast: Dict) -> str:
        """트렌드 분석 텍스트 생성"""
        if len(historical_data) < 2:
            return "데이터가 부족하여 트렌드 분석이 제한됩니다."
        
        recent_avg = np.mean(historical_data[-3:])
        older_avg = np.mean(historical_data[:-3]) if len(historical_data) > 3 else historical_data[0]
        
        growth_rate = ((recent_avg - older_avg) / older_avg * 100) if older_avg != 0 else 0
        
        if growth_rate > 10:
            trend = "강한 성장 추세"
        elif growth_rate > 5:
            trend = "성장 추세"
        elif growth_rate > -5:
            trend = "안정적"
        elif growth_rate > -10:
            trend = "하락 추세"
        else:
            trend = "강한 하락 추세"
        
        return f"최근 매출 트렌드: {trend} (변화율: {growth_rate:.1f}%)"

class WorkEfficiencyService:
    """업무 효율성 분석 서비스"""
    
    def analyze_user_efficiency(self, user: User, start_date: date, end_date: date) -> WorkEfficiencyAnalysis:
        """사용자 업무 효율성 분석"""
        # 업무 세션 데이터 수집
        work_sessions = WorkSession.objects.filter(
            user=user,
            date__range=[start_date, end_date],
            status='completed'
        )
        
        # 기본 지표 계산
        total_hours = sum(ws.duration for ws in work_sessions if ws.duration)
        total_sessions = work_sessions.count()
        
        # 완료율 계산 (예: 완료된 작업 / 전체 작업)
        completion_rate = min(100, (total_sessions / max(1, (end_date - start_date).days)) * 10)
        
        # 평균 업무 시간 계산
        avg_duration = total_hours / total_sessions if total_sessions > 0 else 0
        
        # 효율성 점수 계산 (복합 지표)
        efficiency_score = self._calculate_efficiency_score({
            'completion_rate': completion_rate,
            'avg_duration': avg_duration,
            'consistency': self._calculate_consistency(work_sessions),
            'quality_proxy': min(100, completion_rate * 1.2)  # 간접 품질 지표
        })
        
        # 강점과 약점 분석
        strengths, weaknesses = self._analyze_strengths_weaknesses(work_sessions)
        
        analysis = WorkEfficiencyAnalysis.objects.create(
            analysis_type='individual',
            target_user=user,
            analysis_period_start=start_date,
            analysis_period_end=end_date,
            efficiency_score=efficiency_score,
            task_completion_rate=completion_rate,
            average_task_duration=avg_duration,
            total_work_hours=total_hours,
            productive_hours=total_hours * 0.8,  # 추정값
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=self._generate_recommendations(efficiency_score, weaknesses),
            comparison_data=self._get_comparison_data(user, efficiency_score),
            trend_analysis=self._analyze_efficiency_trend(user, start_date, end_date)
        )
        
        return analysis
    
    def analyze_project_efficiency(self, project: Project) -> WorkEfficiencyAnalysis:
        """프로젝트 업무 효율성 분석"""
        # 프로젝트 관련 작업 세션 수집
        team_members = project.team_members.all()
        work_sessions = WorkSession.objects.filter(
            user__in=team_members,
            date__range=[project.start_date, project.end_date],
            status='completed'
        )
        
        # 프로젝트 진행률 기반 효율성 계산
        progress_rate = project.completion_rate
        time_utilization = self._calculate_time_utilization(work_sessions, project)
        
        efficiency_score = (progress_rate + time_utilization) / 2
        
        analysis = WorkEfficiencyAnalysis.objects.create(
            analysis_type='project',
            target_project=project,
            analysis_period_start=project.start_date,
            analysis_period_end=project.end_date,
            efficiency_score=efficiency_score,
            task_completion_rate=progress_rate,
            total_work_hours=sum(ws.duration for ws in work_sessions if ws.duration),
            recommendations=self._generate_project_recommendations(efficiency_score, project),
            trend_analysis=f"프로젝트 '{project.name}' 효율성 분석"
        )
        
        return analysis
    
    def _calculate_efficiency_score(self, metrics: Dict[str, float]) -> float:
        """효율성 점수 계산"""
        weights = {
            'completion_rate': 0.4,
            'avg_duration': 0.2,
            'consistency': 0.2,
            'quality_proxy': 0.2
        }
        
        # 평균 업무 시간은 역수로 계산 (짧을수록 좋음)
        normalized_duration = min(100, 8 / max(0.1, metrics['avg_duration']) * 100)
        
        score = (
            metrics['completion_rate'] * weights['completion_rate'] +
            normalized_duration * weights['avg_duration'] +
            metrics['consistency'] * weights['consistency'] +
            metrics['quality_proxy'] * weights['quality_proxy']
        )
        
        return min(100, max(0, score))
    
    def _calculate_consistency(self, work_sessions) -> float:
        """업무 일관성 계산"""
        if work_sessions.count() < 2:
            return 50
        
        daily_hours = {}
        for session in work_sessions:
            date_key = session.date
            daily_hours[date_key] = daily_hours.get(date_key, 0) + (session.duration or 0)
        
        if len(daily_hours) < 2:
            return 50
        
        hours_list = list(daily_hours.values())
        std_dev = np.std(hours_list)
        mean_hours = np.mean(hours_list)
        
        consistency = max(0, 100 - (std_dev / max(0.1, mean_hours) * 100))
        return min(100, consistency)
    
    def _analyze_strengths_weaknesses(self, work_sessions) -> Tuple[List[str], List[str]]:
        """강점과 약점 분석"""
        strengths = []
        weaknesses = []
        
        if work_sessions.count() > 0:
            avg_hours = np.mean([ws.duration for ws in work_sessions if ws.duration])
            
            if avg_hours > 6:
                strengths.append("높은 업무 집중도")
            elif avg_hours < 3:
                weaknesses.append("낮은 업무 투입 시간")
            
            # 일관성 체크
            consistency = self._calculate_consistency(work_sessions)
            if consistency > 70:
                strengths.append("일관된 업무 패턴")
            elif consistency < 50:
                weaknesses.append("불규칙한 업무 패턴")
        
        return strengths, weaknesses
    
    def _generate_recommendations(self, efficiency_score: float, weaknesses: List[str]) -> List[str]:
        """개선 권고사항 생성"""
        recommendations = []
        
        if efficiency_score < 70:
            recommendations.append("업무 효율성 개선을 위한 시간 관리 교육 권장")
            recommendations.append("업무 우선순위 설정 방법 개선")
        
        if "불규칙한 업무 패턴" in weaknesses:
            recommendations.append("규칙적인 업무 스케줄 수립")
            recommendations.append("일일 업무 계획 수립 습관화")
        
        if "낮은 업무 투입 시간" in weaknesses:
            recommendations.append("업무 집중도 향상 방안 검토")
            recommendations.append("방해 요소 제거 및 집중 환경 조성")
        
        return recommendations
    
    def _get_comparison_data(self, user: User, score: float) -> Dict:
        """비교 데이터 생성"""
        # 전체 평균과 비교
        avg_efficiency = WorkEfficiencyAnalysis.objects.filter(
            analysis_type='individual'
        ).aggregate(avg_score=Avg('efficiency_score'))['avg_score'] or 70
        
        return {
            'user_score': score,
            'company_average': avg_efficiency,
            'percentile': self._calculate_percentile(score),
            'comparison_text': f"회사 평균 대비 {'높음' if score > avg_efficiency else '낮음'}"
        }
    
    def _calculate_percentile(self, score: float) -> float:
        """백분위 계산"""
        all_scores = list(
            WorkEfficiencyAnalysis.objects.filter(analysis_type='individual')
            .values_list('efficiency_score', flat=True)
        )
        
        if not all_scores:
            return 50
        
        percentile = (sum(1 for s in all_scores if s <= score) / len(all_scores)) * 100
        return percentile
    
    def _analyze_efficiency_trend(self, user: User, start_date: date, end_date: date) -> str:
        """효율성 트렌드 분석"""
        previous_analyses = WorkEfficiencyAnalysis.objects.filter(
            target_user=user,
            analysis_period_end__lt=start_date
        ).order_by('-created_at')[:3]
        
        if previous_analyses.count() < 2:
            return "이전 분석 데이터가 부족하여 트렌드 분석이 제한됩니다."
        
        scores = [a.efficiency_score for a in previous_analyses]
        recent_avg = np.mean(scores[:2])
        older_avg = np.mean(scores[2:]) if len(scores) > 2 else scores[-1]
        
        change = recent_avg - older_avg
        if change > 5:
            return f"효율성이 향상되고 있습니다 (+{change:.1f}점)"
        elif change < -5:
            return f"효율성이 저하되고 있습니다 ({change:.1f}점)"
        else:
            return "효율성이 안정적으로 유지되고 있습니다"
    
    def _calculate_time_utilization(self, work_sessions, project: Project) -> float:
        """시간 활용도 계산"""
        total_hours = sum(ws.duration for ws in work_sessions if ws.duration)
        project_days = (project.end_date - project.start_date).days
        expected_hours = project_days * 8 * project.team_members.count()  # 예상 총 작업 시간
        
        utilization = (total_hours / max(1, expected_hours)) * 100
        return min(100, utilization)
    
    def _generate_project_recommendations(self, efficiency_score: float, project: Project) -> List[str]:
        """프로젝트 개선 권고사항"""
        recommendations = []
        
        if efficiency_score < 70:
            recommendations.append("프로젝트 일정 재검토 필요")
            recommendations.append("팀원 역할 분담 최적화")
        
        if project.completion_rate < 50:
            recommendations.append("진행 상황 모니터링 강화")
            recommendations.append("중간 점검 미팅 증설")
        
        return recommendations

class PerformanceAnalysisService:
    """성과 분석 서비스"""
    
    def analyze_sales_performance(self, user: User, start_date: date, end_date: date) -> PerformanceAnalysis:
        """영업 성과 분석"""
        # 영업 실적 데이터 수집
        sales_records = RevenueRecord.objects.filter(
            sales_person=user,
            revenue_date__range=[start_date, end_date],
            is_confirmed=True
        )
        
        total_revenue = sales_records.aggregate(total=Sum('net_amount'))['total'] or Decimal('0')
        total_deals = sales_records.count()
        
        # 목표 대비 달성률 계산
        target = RevenueTarget.objects.filter(
            assigned_user=user,
            target_type='monthly',
            year=start_date.year,
            month=start_date.month
        ).first()
        
        achievement_rate = 0
        if target:
            achievement_rate = float(total_revenue / target.target_amount * 100)
        
        # KPI 점수 계산
        kpi_scores = {
            'revenue_achievement': min(100, achievement_rate),
            'deal_count': min(100, total_deals * 10),  # 딜 수 기준
            'average_deal_size': self._calculate_deal_size_score(sales_records),
            'conversion_rate': self._calculate_conversion_rate(user, start_date, end_date)
        }
        
        overall_score = sum(kpi_scores.values()) / len(kpi_scores)
        
        analysis = PerformanceAnalysis.objects.create(
            performance_type='sales',
            title=f"{user.get_full_name()} 영업 성과 분석",
            target_user=user,
            analysis_period_start=start_date,
            analysis_period_end=end_date,
            overall_score=overall_score,
            kpi_scores=kpi_scores,
            target_achievement_rate=achievement_rate,
            revenue_generated=total_revenue,
            achievements=self._identify_achievements(kpi_scores),
            challenges=self._identify_challenges(kpi_scores),
            improvement_areas=self._suggest_improvement_areas(kpi_scores),
            qualitative_assessment=self._generate_qualitative_assessment(overall_score)
        )
        
        return analysis
    
    def analyze_project_performance(self, project: Project) -> PerformanceAnalysis:
        """프로젝트 성과 분석"""
        # 프로젝트 관련 지표 계산
        completion_rate = project.completion_rate
        revenue_performance = float(project.total_revenue / project.contract_amount * 100) if project.contract_amount > 0 else 0
        
        # 일정 준수율 계산
        days_total = (project.end_date - project.start_date).days
        days_passed = (timezone.now().date() - project.start_date).days
        schedule_performance = min(100, (completion_rate / max(1, (days_passed / days_total) * 100)) * 100)
        
        kpi_scores = {
            'completion_rate': completion_rate,
            'revenue_performance': revenue_performance,
            'schedule_performance': schedule_performance,
            'budget_performance': self._calculate_budget_performance(project)
        }
        
        overall_score = sum(kpi_scores.values()) / len(kpi_scores)
        
        analysis = PerformanceAnalysis.objects.create(
            performance_type='project',
            title=f"프로젝트 '{project.name}' 성과 분석",
            target_project=project,
            analysis_period_start=project.start_date,
            analysis_period_end=project.end_date,
            overall_score=overall_score,
            kpi_scores=kpi_scores,
            target_achievement_rate=completion_rate,
            revenue_generated=project.total_revenue,
            achievements=self._identify_project_achievements(project, kpi_scores),
            challenges=self._identify_project_challenges(project, kpi_scores),
            improvement_areas=self._suggest_project_improvements(kpi_scores),
            qualitative_assessment=f"프로젝트 진행률 {completion_rate:.1f}%, 전반적 성과 {'양호' if overall_score > 70 else '개선 필요'}"
        )
        
        return analysis
    
    def _calculate_deal_size_score(self, sales_records) -> float:
        """평균 거래 규모 점수"""
        if not sales_records.exists():
            return 0
        
        avg_deal_size = sales_records.aggregate(avg=Avg('net_amount'))['avg']
        
        # 업계 평균과 비교 (임의 기준)
        industry_avg = Decimal('5000000')  # 500만원
        
        score = min(100, float(avg_deal_size / industry_avg * 100))
        return score
    
    def _calculate_conversion_rate(self, user: User, start_date: date, end_date: date) -> float:
        """전환율 계산 (간접 추정)"""
        # 실제 CRM 데이터가 없으므로 매출 기록 기반으로 추정
        confirmed_deals = RevenueRecord.objects.filter(
            sales_person=user,
            revenue_date__range=[start_date, end_date],
            is_confirmed=True
        ).count()
        
        # 추정 전환율 (실제로는 리드/기회 데이터가 필요)
        estimated_leads = max(confirmed_deals * 3, 10)  # 추정값
        conversion_rate = (confirmed_deals / estimated_leads) * 100
        
        return min(100, conversion_rate)
    
    def _calculate_budget_performance(self, project: Project) -> float:
        """예산 성과 계산"""
        # 실제 비용 데이터가 없으므로 매출 기반으로 추정
        revenue_ratio = float(project.total_revenue / project.contract_amount) if project.contract_amount > 0 else 0
        
        # 매출 비율이 높을수록 예산 성과 양호로 가정
        return min(100, revenue_ratio * 120)  # 가중치 적용
    
    def _identify_achievements(self, kpi_scores: Dict[str, float]) -> List[str]:
        """주요 성과 식별"""
        achievements = []
        
        for kpi, score in kpi_scores.items():
            if score > 90:
                achievements.append(f"{kpi} 분야에서 뛰어난 성과 ({score:.1f}점)")
            elif score > 80:
                achievements.append(f"{kpi} 분야에서 우수한 성과 ({score:.1f}점)")
        
        return achievements
    
    def _identify_challenges(self, kpi_scores: Dict[str, float]) -> List[str]:
        """도전 과제 식별"""
        challenges = []
        
        for kpi, score in kpi_scores.items():
            if score < 60:
                challenges.append(f"{kpi} 분야에서 개선 필요 ({score:.1f}점)")
            elif score < 70:
                challenges.append(f"{kpi} 분야에서 주의 필요 ({score:.1f}점)")
        
        return challenges
    
    def _suggest_improvement_areas(self, kpi_scores: Dict[str, float]) -> List[str]:
        """개선 영역 제안"""
        improvements = []
        
        lowest_kpi = min(kpi_scores, key=kpi_scores.get)
        improvements.append(f"{lowest_kpi} 개선에 우선 집중")
        
        if kpi_scores.get('conversion_rate', 0) < 70:
            improvements.append("리드 관리 및 영업 프로세스 개선")
        
        if kpi_scores.get('revenue_achievement', 0) < 80:
            improvements.append("목표 달성을 위한 액션 플랜 수립")
        
        return improvements
    
    def _identify_project_achievements(self, project: Project, kpi_scores: Dict[str, float]) -> List[str]:
        """프로젝트 주요 성과"""
        achievements = []
        
        if kpi_scores.get('completion_rate', 0) > 80:
            achievements.append("높은 프로젝트 진행률 달성")
        
        if kpi_scores.get('schedule_performance', 0) > 90:
            achievements.append("일정 준수 우수")
        
        return achievements
    
    def _identify_project_challenges(self, project: Project, kpi_scores: Dict[str, float]) -> List[str]:
        """프로젝트 도전 과제"""
        challenges = []
        
        if kpi_scores.get('schedule_performance', 0) < 70:
            challenges.append("일정 지연 리스크")
        
        if kpi_scores.get('completion_rate', 0) < 50:
            challenges.append("진행률 저조")
        
        return challenges
    
    def _suggest_project_improvements(self, kpi_scores: Dict[str, float]) -> List[str]:
        """프로젝트 개선 제안"""
        improvements = []
        
        if kpi_scores.get('schedule_performance', 0) < 80:
            improvements.append("일정 관리 강화")
            improvements.append("리소스 재배치 검토")
        
        return improvements
    
    def _generate_qualitative_assessment(self, overall_score: float) -> str:
        """정성적 평가 생성"""
        if overall_score > 90:
            return "탁월한 성과를 보이고 있습니다. 현재 수준을 유지하며 추가적인 도전 과제를 설정하는 것을 권장합니다."
        elif overall_score > 80:
            return "우수한 성과를 달성했습니다. 일부 영역에서 추가적인 개선을 통해 더욱 향상시킬 수 있습니다."
        elif overall_score > 70:
            return "전반적으로 양호한 성과입니다. 몇 가지 개선 영역에 집중하여 성과를 한 단계 높일 수 있습니다."
        elif overall_score > 60:
            return "평균 수준의 성과입니다. 주요 개선 영역을 파악하고 체계적인 개선 계획이 필요합니다."
        else:
            return "개선이 필요한 상황입니다. 근본적인 원인 분석과 함께 단계적 개선 전략을 수립해야 합니다."

class AnomalyDetectionService:
    """이상 패턴 감지 서비스"""
    
    def __init__(self):
        self.ml_service = SimpleMLService()
    
    def detect_revenue_anomalies(self) -> List[AnomalyDetection]:
        """매출 이상 패턴 감지"""
        # 최근 3개월 일별 매출 데이터
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=90)
        
        daily_revenues = self._get_daily_revenue_data(start_date, end_date)
        
        # 이상 탐지 실행
        anomalies = self.ml_service.detect_anomalies(daily_revenues, threshold=2.0)
        
        detected_anomalies = []
        for anomaly in anomalies:
            anomaly_date = start_date + timedelta(days=anomaly['index'])
            
            # 이상 유형 결정
            if anomaly['value'] > anomaly['expected_range'][1]:
                anomaly_type = 'revenue_spike'
                description = f"매출이 예상보다 {anomaly['value'] - anomaly['expected_range'][1]:,.0f}원 높습니다."
            else:
                anomaly_type = 'revenue_drop'
                description = f"매출이 예상보다 {anomaly['expected_range'][0] - anomaly['value']:,.0f}원 낮습니다."
            
            detection = AnomalyDetection.objects.create(
                anomaly_type=anomaly_type,
                severity=anomaly['severity'],
                data_source='daily_revenue',
                affected_metric='일별 매출',
                expected_value=sum(anomaly['expected_range']) / 2,
                actual_value=anomaly['value'],
                deviation_percentage=abs(anomaly['value'] - sum(anomaly['expected_range']) / 2) / sum(anomaly['expected_range']) * 2 * 100,
                description=description,
                possible_causes=self._identify_revenue_anomaly_causes(anomaly_type),
                recommended_actions=self._recommend_revenue_actions(anomaly_type),
                impact_assessment=f"일별 매출에서 {anomaly['severity']} 수준의 이상 패턴 감지"
            )
            
            detected_anomalies.append(detection)
        
        return detected_anomalies
    
    def detect_efficiency_anomalies(self, user: User) -> List[AnomalyDetection]:
        """업무 효율성 이상 패턴 감지"""
        # 최근 30일 일별 작업 시간 데이터
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        daily_hours = self._get_daily_work_hours(user, start_date, end_date)
        
        anomalies = self.ml_service.detect_anomalies(daily_hours, threshold=1.5)
        
        detected_anomalies = []
        for anomaly in anomalies:
            detection = AnomalyDetection.objects.create(
                anomaly_type='efficiency_drop' if anomaly['value'] < anomaly['expected_range'][0] else 'pattern_change',
                severity=anomaly['severity'],
                data_source='work_sessions',
                affected_metric='일별 근무 시간',
                related_user=user,
                expected_value=sum(anomaly['expected_range']) / 2,
                actual_value=anomaly['value'],
                deviation_percentage=abs(anomaly['z_score']) * 10,
                description=f"사용자의 일별 근무 패턴에서 이상이 감지되었습니다.",
                possible_causes=['개인적 사유', '업무량 변화', '시스템 오류', '건강 상태'],
                recommended_actions=['개별 면담 실시', '업무량 조정 검토', '건강 상태 확인'],
                impact_assessment="개인 생산성에 영향을 미칠 수 있음"
            )
            
            detected_anomalies.append(detection)
        
        return detected_anomalies
    
    def _get_daily_revenue_data(self, start_date: date, end_date: date) -> List[float]:
        """일별 매출 데이터 조회"""
        daily_data = []
        current_date = start_date
        
        while current_date <= end_date:
            day_revenue = RevenueRecord.objects.filter(
                revenue_date=current_date,
                is_confirmed=True
            ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0')
            
            daily_data.append(float(day_revenue))
            current_date += timedelta(days=1)
        
        return daily_data
    
    def _get_daily_work_hours(self, user: User, start_date: date, end_date: date) -> List[float]:
        """일별 근무 시간 데이터 조회"""
        daily_hours = []
        current_date = start_date
        
        while current_date <= end_date:
            day_hours = WorkSession.objects.filter(
                user=user,
                date=current_date,
                status='completed'
            ).aggregate(total=Sum('duration'))['total'] or 0
            
            daily_hours.append(float(day_hours))
            current_date += timedelta(days=1)
        
        return daily_hours
    
    def _identify_revenue_anomaly_causes(self, anomaly_type: str) -> List[str]:
        """매출 이상 패턴 원인 분석"""
        if anomaly_type == 'revenue_spike':
            return [
                '대형 계약 체결',
                '계절적 수요 증가',
                '마케팅 캠페인 효과',
                '시장 상황 변화'
            ]
        else:  # revenue_drop
            return [
                '계약 지연 또는 취소',
                '경쟁사 영향',
                '시장 침체',
                '내부 운영 이슈',
                '시즌적 요인'
            ]
    
    def _recommend_revenue_actions(self, anomaly_type: str) -> List[str]:
        """매출 이상 패턴 대응 방안"""
        if anomaly_type == 'revenue_spike':
            return [
                '성공 요인 분석 및 표준화',
                '추가 영업 기회 발굴',
                '리소스 확대 검토'
            ]
        else:  # revenue_drop
            return [
                '원인 분석 및 대응 계획 수립',
                '영업팀과의 긴급 미팅 소집',
                '고객 관계 점검',
                '마케팅 전략 재검토'
            ]

class AIInsightService:
    """AI 인사이트 생성 서비스"""
    
    def generate_revenue_insights(self) -> List[AIInsight]:
        """매출 관련 인사이트 생성"""
        insights = []
        
        # 매출 트렌드 분석
        trend_insight = self._analyze_revenue_trend()
        if trend_insight:
            insights.append(trend_insight)
        
        # 고객별 매출 분석
        customer_insight = self._analyze_customer_revenue()
        if customer_insight:
            insights.append(customer_insight)
        
        # 예측 vs 실제 분석
        prediction_insight = self._analyze_prediction_accuracy()
        if prediction_insight:
            insights.append(prediction_insight)
        
        return insights
    
    def generate_efficiency_insights(self) -> List[AIInsight]:
        """효율성 관련 인사이트 생성"""
        insights = []
        
        # 팀 효율성 벤치마킹
        team_insight = self._benchmark_team_efficiency()
        if team_insight:
            insights.append(team_insight)
        
        # 작업 패턴 최적화
        pattern_insight = self._optimize_work_patterns()
        if pattern_insight:
            insights.append(pattern_insight)
        
        return insights
    
    def _analyze_revenue_trend(self) -> Optional[AIInsight]:
        """매출 트렌드 분석 인사이트"""
        # 최근 6개월 매출 데이터 분석
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=180)
        
        monthly_revenues = []
        current_date = start_date.replace(day=1)
        
        while current_date <= end_date:
            next_month = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1)
            month_revenue = RevenueRecord.objects.filter(
                revenue_date__gte=current_date,
                revenue_date__lt=next_month,
                is_confirmed=True
            ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0')
            
            monthly_revenues.append(float(month_revenue))
            current_date = next_month
        
        if len(monthly_revenues) < 3:
            return None
        
        # 트렌드 계산
        growth_rate = ((monthly_revenues[-1] - monthly_revenues[0]) / max(monthly_revenues[0], 1)) * 100
        
        # 인사이트 생성
        if abs(growth_rate) > 20:
            priority = 'high'
        elif abs(growth_rate) > 10:
            priority = 'medium'
        else:
            priority = 'low'
        
        trend_direction = "증가" if growth_rate > 0 else "감소"
        
        insight = AIInsight.objects.create(
            insight_type='trend',
            title=f"매출 {trend_direction} 트렌드 감지",
            priority=priority,
            summary=f"최근 6개월간 매출이 {abs(growth_rate):.1f}% {trend_direction}했습니다.",
            detailed_analysis=f"월별 매출 분석 결과, 지속적인 {trend_direction} 패턴이 관찰됩니다. "
                            f"이는 {'긍정적인' if growth_rate > 0 else '우려스러운'} 신호로 해석됩니다.",
            key_findings=[
                f"6개월 성장률: {growth_rate:.1f}%",
                f"최근 3개월 평균: {np.mean(monthly_revenues[-3:]):,.0f}원",
                f"변동성: {np.std(monthly_revenues):.0f}"
            ],
            supporting_data={
                'monthly_revenues': monthly_revenues,
                'growth_rate': growth_rate,
                'trend_direction': trend_direction
            },
            actionable_recommendations=self._get_trend_recommendations(growth_rate),
            data_confidence=85.0,
            target_audience=['management', 'sales_team'],
            affected_areas=['revenue', 'strategy']
        )
        
        return insight
    
    def _analyze_customer_revenue(self) -> Optional[AIInsight]:
        """고객별 매출 분석 인사이트"""
        # 상위 고객 집중도 분석
        top_customers = RevenueRecord.objects.filter(
            is_confirmed=True,
            revenue_date__gte=timezone.now().date() - timedelta(days=365)
        ).values('client__name').annotate(
            total_revenue=Sum('net_amount')
        ).order_by('-total_revenue')[:5]
        
        if not top_customers:
            return None
        
        total_revenue = sum(c['total_revenue'] for c in top_customers)
        overall_revenue = RevenueRecord.objects.filter(
            is_confirmed=True,
            revenue_date__gte=timezone.now().date() - timedelta(days=365)
        ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0')
        
        concentration_ratio = (total_revenue / float(overall_revenue)) * 100 if overall_revenue > 0 else 0
        
        if concentration_ratio > 70:
            priority = 'high'
            risk_level = '높음'
        elif concentration_ratio > 50:
            priority = 'medium'
            risk_level = '보통'
        else:
            priority = 'low'
            risk_level = '낮음'
        
        insight = AIInsight.objects.create(
            insight_type='risk',
            title=f"고객 집중도 리스크 분석",
            priority=priority,
            summary=f"상위 5개 고객이 전체 매출의 {concentration_ratio:.1f}%를 차지합니다.",
            detailed_analysis=f"고객 집중도가 {risk_level} 수준으로, " + ("다변화 전략이 필요" if concentration_ratio > 50 else "적절한 분산") + "됩니다.",
            key_findings=[
                f"고객 집중도: {concentration_ratio:.1f}%",
                f"상위 고객 수: 5개",
                f"리스크 수준: {risk_level}"
            ],
            supporting_data={
                'concentration_ratio': concentration_ratio,
                'top_customers': list(top_customers)
            },
            actionable_recommendations=self._get_customer_diversification_recommendations(concentration_ratio),
            data_confidence=90.0,
            target_audience=['management', 'sales_team'],
            affected_areas=['revenue', 'risk_management']
        )
        
        return insight
    
    def _analyze_prediction_accuracy(self) -> Optional[AIInsight]:
        """예측 정확도 분석"""
        validated_predictions = RevenuePrediction.objects.filter(
            is_validated=True,
            actual_amount__isnull=False
        )
        
        if validated_predictions.count() < 3:
            return None
        
        accuracies = []
        for pred in validated_predictions:
            accuracy = pred.calculate_accuracy()
            if accuracy is not None:
                accuracies.append(accuracy)
        
        if not accuracies:
            return None
        
        avg_accuracy = np.mean(accuracies)
        
        insight = AIInsight.objects.create(
            insight_type='optimization',
            title="예측 모델 성능 분석",
            priority='medium',
            summary=f"매출 예측 모델의 평균 정확도는 {avg_accuracy:.1f}%입니다.",
            detailed_analysis=f"예측 모델의 성능을 분석한 결과, {'우수한' if avg_accuracy > 80 else '개선이 필요한'} 수준입니다.",
            key_findings=[
                f"평균 정확도: {avg_accuracy:.1f}%",
                f"검증된 예측 수: {len(accuracies)}개",
                f"최고 정확도: {max(accuracies):.1f}%",
                f"최저 정확도: {min(accuracies):.1f}%"
            ],
            supporting_data={
                'accuracies': accuracies,
                'average_accuracy': avg_accuracy
            },
            actionable_recommendations=self._get_model_improvement_recommendations(avg_accuracy),
            data_confidence=95.0,
            target_audience=['management', 'analysts'],
            affected_areas=['forecasting', 'model_optimization']
        )
        
        return insight
    
    def _benchmark_team_efficiency(self) -> Optional[AIInsight]:
        """팀 효율성 벤치마킹"""
        team_analyses = WorkEfficiencyAnalysis.objects.filter(
            analysis_type='individual',
            created_at__gte=timezone.now() - timedelta(days=90)
        ).values('target_user__username', 'efficiency_score')
        
        if team_analyses.count() < 3:
            return None
        
        scores = [a['efficiency_score'] for a in team_analyses]
        avg_score = np.mean(scores)
        std_score = np.std(scores)
        
        # 성과 격차 분석
        high_performers = [s for s in scores if s > avg_score + std_score]
        low_performers = [s for s in scores if s < avg_score - std_score]
        
        insight = AIInsight.objects.create(
            insight_type='benchmark',
            title="팀 효율성 격차 분석",
            priority='medium',
            summary=f"팀 내 효율성 점수 격차가 {std_score:.1f}점으로 측정됩니다.",
            detailed_analysis=f"팀 평균 효율성은 {avg_score:.1f}점이며, 상위 성과자와 하위 성과자 간 격차가 존재합니다.",
            key_findings=[
                f"팀 평균 점수: {avg_score:.1f}점",
                f"표준편차: {std_score:.1f}점",
                f"상위 성과자: {len(high_performers)}명",
                f"하위 성과자: {len(low_performers)}명"
            ],
            supporting_data={
                'team_scores': scores,
                'statistics': {
                    'mean': avg_score,
                    'std': std_score,
                    'min': min(scores),
                    'max': max(scores)
                }
            },
            actionable_recommendations=[
                "상위 성과자의 베스트 프랙티스 공유",
                "하위 성과자 대상 집중 코칭 실시",
                "효율성 격차 해소를 위한 교육 프로그램 운영"
            ],
            data_confidence=88.0,
            target_audience=['management', 'hr_team'],
            affected_areas=['team_management', 'performance']
        )
        
        return insight
    
    def _optimize_work_patterns(self) -> Optional[AIInsight]:
        """작업 패턴 최적화 인사이트"""
        # 시간대별 생산성 분석 (간접 추정)
        work_sessions = WorkSession.objects.filter(
            date__gte=timezone.now().date() - timedelta(days=30),
            status='completed',
            duration__isnull=False
        )
        
        if work_sessions.count() < 10:
            return None
        
        # 시간대별 평균 작업 시간 계산
        hourly_productivity = {}
        for session in work_sessions:
            hour = session.start_time.hour if session.start_time else 9
            if hour not in hourly_productivity:
                hourly_productivity[hour] = []
            hourly_productivity[hour].append(session.duration)
        
        # 최고 생산성 시간대 찾기
        best_hours = []
        for hour, durations in hourly_productivity.items():
            if len(durations) >= 3:  # 최소 데이터 확보
                avg_duration = np.mean(durations)
                best_hours.append((hour, avg_duration))
        
        if not best_hours:
            return None
        
        best_hours.sort(key=lambda x: x[1], reverse=True)
        peak_hour = best_hours[0][0]
        peak_productivity = best_hours[0][1]
        
        insight = AIInsight.objects.create(
            insight_type='optimization',
            title="최적 작업 시간대 분석",
            priority='low',
            summary=f"팀의 최고 생산성 시간대는 {peak_hour}시입니다.",
            detailed_analysis=f"{peak_hour}시 시간대에 평균 {peak_productivity:.1f}시간의 집중 작업이 이루어집니다.",
            key_findings=[
                f"최고 생산성 시간: {peak_hour}시",
                f"평균 집중 시간: {peak_productivity:.1f}시간",
                f"분석 기간: 최근 30일"
            ],
            supporting_data={
                'hourly_productivity': hourly_productivity,
                'peak_hour': peak_hour,
                'peak_productivity': peak_productivity
            },
            actionable_recommendations=[
                f"{peak_hour}시 시간대에 중요한 업무 배치",
                "회의 시간을 비생산적 시간대로 이동",
                "개인별 생산성 패턴 분석 확대"
            ],
            data_confidence=75.0,
            target_audience=['management', 'team_leads'],
            affected_areas=['productivity', 'scheduling']
        )
        
        return insight
    
    def _get_trend_recommendations(self, growth_rate: float) -> List[str]:
        """트렌드 기반 권고사항"""
        if growth_rate > 20:
            return [
                "성장 동력 분석 및 확대 방안 검토",
                "리소스 확충 계획 수립",
                "시장 기회 적극 활용"
            ]
        elif growth_rate > 0:
            return [
                "현재 성장 모멘텀 유지",
                "추가 성장 기회 발굴",
                "효율성 개선을 통한 성장 가속화"
            ]
        elif growth_rate > -10:
            return [
                "성장 둔화 원인 분석",
                "새로운 수익원 발굴",
                "비용 최적화 검토"
            ]
        else:
            return [
                "긴급 대응 계획 수립",
                "사업 구조 재검토",
                "시장 전략 전면 재수립"
            ]
    
    def _get_customer_diversification_recommendations(self, concentration_ratio: float) -> List[str]:
        """고객 다변화 권고사항"""
        if concentration_ratio > 70:
            return [
                "신규 고객 발굴 전략 수립",
                "기존 고객 의존도 단계적 감소",
                "시장 세분화 및 타겟팅 다양화",
                "리스크 관리 체계 강화"
            ]
        elif concentration_ratio > 50:
            return [
                "고객 포트폴리오 균형 조정",
                "중간 규모 고객층 확대",
                "고객 관계 관리 강화"
            ]
        else:
            return [
                "현재 고객 다변화 수준 유지",
                "고객별 수익성 최적화",
                "장기 고객 관계 강화"
            ]
    
    def _get_model_improvement_recommendations(self, accuracy: float) -> List[str]:
        """모델 개선 권고사항"""
        if accuracy > 85:
            return [
                "현재 모델 성능 유지",
                "새로운 변수 추가 검토",
                "예측 범위 확대 고려"
            ]
        elif accuracy > 70:
            return [
                "모델 파라미터 최적화",
                "추가 데이터 수집",
                "앙상블 모델 적용 검토"
            ]
        else:
            return [
                "모델 알고리즘 재검토",
                "데이터 품질 개선",
                "전문가 피드백 반영",
                "대안 모델 개발"
            ]