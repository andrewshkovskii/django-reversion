#-*- coding: utf-8 -*-
__author__ = 'Andrewshkovskii'

from django.forms.forms import Form
from django.views.generic import ListView, FormView
from django.shortcuts import  render_to_response
from django.template.defaultfilters import date as _date
from django.template.context import RequestContext
from reversion.models import Revision, RevertError
import reversion


reversion_does_not_exist_message = u"Ревизия <strong>#{0}</strong> не существует!"
integrity_error_message = u"При попытке восстановить ревизию {0} произошла ошибка целостности БД."
has_no_perm_message = u'У Вас нет прав на восстановление данной ревизии.'
revision_revert_comment_template = u'Восстановление ревизии #{0} от {1} ({2}).'
revision_list_template_title = u'Ревизии {0}'

class RevisionsListView(ListView):
    context_object_name = 'revision_list'
    template_name = 'ip_pbx_reversion/revision_list.html'

    def get_revisioned_object(self, request, *args, **kwargs):
        return self.model.objects.get(**kwargs)

    def get(self, request, *args, **kwargs):
        self.object_list = [version.revision for version in reversion.get_for_object(self.get_revisioned_object(request, *args, **kwargs))]
        return self.render_to_response(self.get_context_data(object_list=self.object_list))

    def get_context_data(self, **kwargs):
        return super(RevisionsListView, self).get_context_data(template_title = revision_list_template_title.format(self.model._meta.verbose_name_plural),
            model_verbose_name = self.model._meta.verbose_name,
            **kwargs)

class RevisionRevertFormView(FormView):
    template_name = "ip_pbx_reversion/revision_revert.html"
    form_class = Form
    back_url = None
    model = None

    def get(self, request, *args, **kwargs):
        if request.user.has_perm("{0}.can_revert_{1}".format(self.model._meta.app_label, self.model.__name__)):
            try:
                revision = Revision.objects.get(pk = kwargs.get('pk'))
            except Revision.DoesNotExist:
                return render_to_response("ip_pbx_reversion/revision_error.html",
                        {'back_url' :  self.back_url, "error_message" : reversion_does_not_exist_message.format(kwargs.get('pk'))},
                    context_instance = RequestContext(request))
            else:
                return self.render_to_response(self.get_context_data(revision = revision,
                    form = self.form_class(),
                    verbose_name = self.model._meta.verbose_name,
                    back_url = self.back_url))
        else:
            return render_to_response("ip_pbx_reversion/revision_error.html",
                    {'back_url' :  self.back_url, "error_message":has_no_perm_message},
                context_instance = RequestContext(request))

    def post(self, request, *args, **kwargs):
        if request.user.has_perm("{0}.can_revert_{1}".format(self.model._meta.app_label, self.model.__name__)):
            try:
                revision = Revision.objects.get(pk = kwargs.get('pk'))
                revision.revert()
                reversion.set_comment(revision_revert_comment_template.format(revision.pk, _date(revision.date_created, "d E H:i:s"), revision.comment))
                return render_to_response("ip_pbx_reversion/revision_revert_success.html",
                        {'back_url' : self.back_url, 'revision' : revision},
                    context_instance = RequestContext(request))
            except Revision.DoesNotExist:
                return render_to_response("ip_pbx_reversion/revision_error.html",
                        {'back_url' : self.back_url, "error_message": reversion_does_not_exist_message.format(kwargs.get('pk'))},
                    context_instance = RequestContext(request))
            except RevertError:
                return render_to_response("ip_pbx_reversion/revision_error.html",
                        {'back_url' : self.back_url, 'error_message' : integrity_error_message.format(kwargs.get('pk'))},
                    context_instance = RequestContext(request))
        else:
            return render_to_response("ip_pbx_reversion/revision_error.html",
                    {'back_url' : self.back_url, "error_message":has_no_perm_message},
                context_instance = RequestContext(request))