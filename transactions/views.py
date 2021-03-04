from dateutil.relativedelta import relativedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, ListView
import json,csv
from django.core.serializers.json import DjangoJSONEncoder
from transactions.constants import DEPOSIT, WITHDRAWAL,ENQUIRY,DOWNLOAD
from transactions.forms import (
    DepositForm,
    TransactionDateRangeForm,
    WithdrawForm,
    EnquiryForm,
    DownloadForm,
)
from transactions.models import Transaction
from django.core.mail import send_mail
from django.forms.models import model_to_dict


class TransactionRepostView(LoginRequiredMixin, ListView):
    template_name = 'transactions/transaction_report.html'
    model = Transaction
    form_data = {}

    def get(self, request, *args, **kwargs):
        form = TransactionDateRangeForm(request.GET or None)
        if form.is_valid():
            self.form_data = form.cleaned_data

        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset().filter(
            account=self.request.user.account
        )

        daterange = self.form_data.get("daterange")

        if daterange:
            queryset = queryset.filter(timestamp__date__range=daterange)


        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'account': self.request.user.account,
            'form': TransactionDateRangeForm(self.request.GET or None)
        })
        return context


class TransactionCreateMixin(LoginRequiredMixin, CreateView):
    template_name = 'transactions/transaction_form.html'
    model = Transaction
    title = ''
    success_url = reverse_lazy('transactions:transaction_report')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'account': self.request.user.account
        })
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': self.title
        })

        return context


class DepositMoneyView(TransactionCreateMixin):
    form_class = DepositForm
    title = 'Deposit Money to Your Account'

    def get_initial(self):
        initial = {'transaction_type': DEPOSIT}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account
        if not account.initial_deposit_date:
            now = timezone.now()
            next_interest_month = int(
                12 / account.account_type.interest_calculation_per_year
            )
            account.initial_deposit_date = now
            account.interest_start_date = (
                now + relativedelta(
                    months=+next_interest_month
                )
            )

        account.balance += amount
        account.save(
            update_fields=[
                'initial_deposit_date',
                'balance',
                'interest_start_date'
            ]
        )

        send_mail(
            'Amount Deposited!!!!!!!!!!',
            f'{amount}$ was deposited to your account successfully',
            'shinbipin@gmail.com',
            [self.request.user.email],
            fail_silently=False,
        )

        messages.success(
            self.request,
            f'{amount}$ was deposited to your account successfully'
        )

        return super().form_valid(form)


class WithdrawMoneyView(TransactionCreateMixin):
    form_class = WithdrawForm
    title = 'Withdraw Money from Your Account'

    def get_initial(self):
        initial = {'transaction_type': WITHDRAWAL}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')

        self.request.user.account.balance -= form.cleaned_data.get('amount')
        self.request.user.account.save(update_fields=['balance'])

        send_mail(
            'Amount Withdraw!!!!!!!!!!',
            f'{amount}$ was debited from your account successfully',
            'shinbipin@gmail.com',
            [self.request.user.email],
            fail_silently=False,
        )
        messages.success(
            self.request,
            f'Successfully withdrawn {amount}$ from your account'
        )

        return super().form_valid(form)

class EnquiryView(TransactionCreateMixin):
    template_name = 'transactions/enquiry_form.html'
    model = Transaction
    form_class = EnquiryForm
    title = 'Balance in your Account'

    def get_initial(self):
        initial = {'transaction_type': ENQUIRY}
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'account': self.request.user.account,
        })

        return context

from rest_framework.decorators import action
import mimetypes
from django.http import HttpResponse
import os

class DownloadView(LoginRequiredMixin, ListView):
    template_name = 'transactions/downloadform.html'
    model = Transaction
    form_class = DownloadForm
    title = 'Report  Download'
    import mimetypes
    form_data = {}
    def get_initial(self):
        initial = {'transaction_type': DOWNLOAD}
        return initial

    def get_queryset(self):
        queryset = super().get_queryset().filter(
            account=self.request.user.account
        )
        treport = queryset.distinct()
        data=[]
        print(type(model_to_dict(treport[0])))
        for record in treport:
            data.append(model_to_dict(record))
        with open('output1.csv', 'w') as output:
            writer = csv.writer(output)
            writer.writerow(["id", "account","amount","balance_after_transaction","transaction_type"])
            data_list = []
            for item in data:
                data_list.append(item.values())
            for i in data_list:
                    writer.writerow(i)
        return queryset.distinct()

    def get(self, request, *args, **kwargs):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        filename = "output1.csv"
        opfile = open("output1.csv", "r")
        mime_type, _ = mimetypes.guess_type(dir_path)
        response = HttpResponse(opfile, content_type=mime_type)
        response['Content-Disposition'] = "attachment; filename=%s" % filename
        return response

