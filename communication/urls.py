from django.urls import path
from . import views

app_name = 'communication'

urlpatterns = [
    # URL for the message thread for a specific case
    # e.g., /messages/case/1/
    path('case/<int:case_pk>/', views.case_messaging_view, name='case-messaging'),
]