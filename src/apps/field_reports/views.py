from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def reports_status(request):
    """Field reports system status check"""
    return Response({
        'message': 'Field reports system is ready',
        'status': 'success'
    })