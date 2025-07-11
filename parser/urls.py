from django.urls import path
from .views import PDFParseView

urlpatterns = [
    path('', PDFParseView.as_view(), name='pdf_upload'),
]