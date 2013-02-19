#-*- coding: utf-8 -*-
__author__ = 'Andrewshkovskii'

from django.forms.forms import Form
from django.views.generic import ListView, FormView, DeleteView
from django.views.generic.detail import SingleObjectMixin
from django.shortcuts import  render_to_response
from django.template.defaultfilters import date as _date
from django.template.context import RequestContext
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from reversion.models import Revision, RevertError
from reversion.revisions import was_deleted_message, get_object_smart_repr
import reversion

reversion_does_not_exist_message = u"Ревизия <strong>#{0}</strong> не существует!"
revert_latest_revision = u"Восстановление текущей ревизии запрещено."
integrity_error_message = u"При попытке восстановить ревизию {0} произошла ошибка целостности БД."
has_no_perm_message = u'У Вас нет прав на восстановление данной ревизии.'
revision_revert_comment_template = u'Восстановление ревизии #{0} от {1} ({2}).'
revision_list_template_title = u'Ревизии {0}'

class RevisionsListView(ListView):
    context_object_name = 'revision_list'
    template_name = 'reversion/revision_list.html'
    template_header = None

    def get_revisioned_object(self, request, *args, **kwargs):
        return self.model.objects.get(**kwargs)

    def get(self, request, *args, **kwargs):
        self.object_list = [version.revision for version in reversion.get_for_object(self.get_revisioned_object(request, *args, **kwargs))]
        return self.render_to_response(self.get_context_data(object_list=self.object_list))

    def get_context_data(self, **kwargs):
        return super(RevisionsListView, self).get_context_data(template_header = revision_list_template_title.format(self.model._meta.verbose_name_plural) if not self.template_header else self.template_header,
                                                                model_verbose_name = self.model._meta.verbose_name,
                                                                **kwargs)

class CanRevertRevisionMixin(SingleObjectMixin):
    path_to_owner = None

    def get_owner_from_request(self):
        return self.request.user

    def user_can_access_to_revision(self, object):
        if self.path_to_owner:
            return self.model.objects.filter(**{'pk' : object.pk, self.path_to_owner : self.get_owner_from_request()}).exists()
        else:
            raise ImproperlyConfigured('No path to owner provided. Please, provide path to object owner')

    def get_object(self, queryset=None):
        o = super(CanRevertRevisionMixin, self).get_object(queryset=queryset)
        if self.user_can_access_to_revision(o):
            return o
        else:
            raise Http404()

class RevisionRevertFormView(FormView, CanRevertRevisionMixin):
    template_name = "reversion/revision_revert.html"
    form_class = Form
    back_url = None
    model = Revision
    model_on_revision = None

    def get(self, request, *args, **kwargs):
        if request.user.has_perm("{0}.can_revert_{1}".format(self.model_on_revision._meta.app_label, self.model_on_revision.__name__)):
            try:
                self.object = self.get_object()
            except Revision.DoesNotExist:
                return render_to_response("reversion/revision_error.html",
                        {'back_url' :  self.back_url, 
                         "error_message" : reversion_does_not_exist_message.format(kwargs.get('pk'))},
                         context_instance = RequestContext(request))
            else:
                if self.object.pk == self.model.objects.latest("date_created").pk:
                    return render_to_response("reversion/revision_error.html",
                                               {'back_url': self.back_url,
                                                "error_message": revert_latest_revision},
                                               context_instance = RequestContext(request))
                return self.render_to_response(self.get_context_data(revision = self.object,
                                                form = self.form_class(),
                                                verbose_name = self.model_on_revision._meta.verbose_name,
                                                back_url = self.back_url))
        else:
            return render_to_response("reversion/revision_error.html",
                                        {'back_url' :  self.back_url, "error_message":has_no_perm_message},
                                        context_instance = RequestContext(request))

    def post(self, request, *args, **kwargs):
        if request.user.has_perm("{0}.can_revert_{1}".format(self.model_on_revision._meta.app_label, self.model_on_revision.__name__)):
            try:
                self.object = self.get_object()
                if self.object.pk != self.model.objects.latest("date_created").pk:
                    self.object.revert(delete=True)
                    reversion.set_comment(revision_revert_comment_template.format(self.object.pk, _date(self.object.date_created, "d E H:i:s"), self.object.comment))
                    return render_to_response("reversion/revision_revert_success.html",
                                            {'back_url' : self.back_url, 'revision' : self.object},
                                                context_instance = RequestContext(request))
                else:
                    return render_to_response("reversion/revision_error.html",
                                              {'back_url': self.back_url,
                                               "error_message": revert_latest_revision},
                                              context_instance=RequestContext(request))
            except Revision.DoesNotExist:
                return render_to_response("reversion/revision_error.html",
                                            {'back_url': self.back_url,
                                            "error_message": reversion_does_not_exist_message.format(kwargs.get('pk'))},
                                            context_instance=RequestContext(request))
            except RevertError:
                return render_to_response("reversion/revision_error.html",
                                            {'back_url': self.back_url, 'error_message' : integrity_error_message.format(kwargs.get('pk'))},
                                            context_instance = RequestContext(request))
        else:
            return render_to_response("reversion/revision_error.html",
                                    {'back_url' : self.back_url, "error_message":has_no_perm_message},
                                    context_instance = RequestContext(request))


class ReversionDeleteMixin(DeleteView):

    def get_follow_chain_head(self):
        raise NotImplementedError

    def create_revision_after_delete(self, comment = None):
        with reversion.create_revision(manage_manually=True):
            reversion.default_revision_manager.save_revision([self.get_follow_chain_head()], comment=comment if comment else was_deleted_message.format(get_object_smart_repr(self.object)), user = self.request.user)

    def delete(self, request, *args, **kwargs):
        delete = super(ReversionDeleteMixin, self).delete(request, *args, **kwargs)
        self.create_revision_after_delete()
        return delete