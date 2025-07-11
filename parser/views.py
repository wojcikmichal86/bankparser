from django.views import View
from django.shortcuts import render
from .forms import PDFUploadForm
from .modules import detect_bank_and_address, fallback_postfinance_tables
from PyPDF2 import PdfReader
import tabula
import pandas as pd
import tempfile
import os

class PDFParseView(View):
    template_name = "parser/upload.html"

    def get(self, request):
        form = PDFUploadForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = PDFUploadForm(request.POST, request.FILES)
        context = {"form": form}

        if form.is_valid():
            pdf_file = request.FILES["pdf_file"]

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                for chunk in pdf_file.chunks():
                    tmp_file.write(chunk)
                tmp_path = tmp_file.name

            bank, address = detect_bank_and_address(tmp_path)
            context["bank"] = bank
            context["address"] = address

            try:
                dfs = tabula.read_pdf(tmp_path, pages="all", multiple_tables=True)
                dfs = [df for df in dfs if isinstance(df, pd.DataFrame) and not df.empty]

                if not dfs and bank == "PostFinance":
                    dfs = fallback_postfinance_tables(tmp_path)

                context["tables"] = [df.to_html(index=False) for df in dfs]

            except Exception as e:
                context["error"] = str(e)

            finally:
                os.unlink(tmp_path)

        return render(request, self.template_name, context)