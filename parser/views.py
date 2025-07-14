from django.views import View
from django.shortcuts import render
from .forms import PDFUploadForm
from .modules import detect_bank_and_address, get_valid_dfs, fallback_postfinance_tables
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
                # Spróbuj pobrać prawidłowe tabele
                dfs = get_valid_dfs(tmp_path)

                if not dfs and bank == "PostFinance":
                    context["fallback_used"] = True
                    dfs = fallback_postfinance_tables(tmp_path)

                if dfs:
                    context["tables"] = [df.to_html(index=False, classes="table table-striped") for df in dfs]
                else:
                    context["warning"] = "⚠️ Keine gültigen Tabellen gefunden."

            except Exception as e:
                context["error"] = f"❌ Fehler bei der Verarbeitung: {e}"

            finally:
                os.unlink(tmp_path)
        return render(request, self.template_name, context)