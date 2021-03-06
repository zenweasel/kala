import datetime
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.urlresolvers import reverse
from django.db import models
from django.http import HttpResponse
from django.utils.encoding import python_2_unicode_compatible
from uuidfield import UUIDField
from .defs import get_icon_for_mime, get_alt_for_mime
from kala.managers import ActiveManager


@python_2_unicode_compatible
class Document(models.Model):
    project = models.ForeignKey('projects.Project')
    name = models.CharField(max_length=255)
    date = models.DateTimeField()
    removed = models.DateField(null=True)
    mime = models.CharField(max_length=255, null=True)
    is_active = models.BooleanField(default=True)

    objects = ActiveManager()

    class Meta:
        ordering = ['-date', 'name']
        db_table = 'kala_documents'

    def set_active(self, active):
        self.is_active = active
        if not self.is_active:
            self.removed = datetime.date.today()
        self.save()

    def delete(self, using=None):
        DocumentVersion.objects.filter(document=self).delete()
        super(Document, self).delete(using)

    @property
    def uuid(self):
        if not hasattr(self, 'document'):
            self.document = self.get_latest()
        return self.document.uuid

    @property
    def description(self):
        if not hasattr(self, 'document'):
            self.document = self.get_latest()
        return self.document.description

    @property
    def person(self):
        if not hasattr(self, 'document'):
            self.document = self.get_latest()
        return self.document.person

    @property
    def created(self):
        if not hasattr(self, 'document'):
            self.document = self.get_latest()
        return self.document.created

    @property
    def file(self):
        if not hasattr(self, 'document'):
            self.document = self.get_latest()
        return self.document.file

    @property
    def get_icon(self):
        if not hasattr(self, 'document'):
            self.document = self.get_latest()
        return self.document.get_icon()

    @property
    def get_alt(self):
        if not hasattr(self, 'document'):
            self.document = self.get_latest()
        return self.document.get_alt()

    def get_latest(self):
        return DocumentVersion.objects.filter(document=self).latest()

    def list_versions(self):
        return DocumentVersion.objects.filter(document=self).exclude(pk=self.get_latest().pk)

    def __str__(self):
        return self.name


# Document upload functions
def upload_document_to(instance, filename):
    """
    """
    return "%s%s" % (settings.DOCUMENT_ROOT, str(instance.pk))


class DocumentStorage(FileSystemStorage):
    """
    """
    def url(self, name):
        document = Document.objects.get(file=name)
        return unicode(reverse('download_document', args=[str(document.pk)]))
document_file_storage = DocumentStorage(location=settings.DOCUMENT_ROOT)


@python_2_unicode_compatible
class DocumentVersion(models.Model):
    uuid = UUIDField(auto=True, primary_key=True)
    document = models.ForeignKey('Document', null=True)
    file = models.FileField(upload_to=upload_document_to, storage=document_file_storage, max_length=255)
    description = models.TextField(null=True)
    created = models.DateTimeField() # Update save method
    changed = models.DateTimeField(auto_now=True) # Update save method
    mime = models.CharField(max_length=255, null=True)
    person = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True)
    name = models.CharField(max_length=255)

    class Meta:
        get_latest_by = 'created'
        ordering = ['name', 'created']
        db_table = 'kala_document_version'

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None, save_document=True):
        if save_document:
            self.document.name = self.name
            self.document.date = self.created
            self.document.mime = self.mime
            self.document.save()
        super(DocumentVersion, self).save(force_insert, force_update, using, update_fields)

    def delete(self, using=None):
        if Document.objects.filter(pk=self.document.pk).count() < 1:
            self.document.delete()
        super(DocumentVersion, self).delete(using)

    def http_response(self):
        response = HttpResponse(self.file.read(), mimetype=self.mime)
        response['Content-Length'] = self.file.size
        response['Content-Disposition'] = 'attachment; filename=' + self.name
        response['Content-Type'] = self.mime
        return response

    def get_icon(self):
        return get_icon_for_mime(self.mime)

    def get_alt(self):
        return get_alt_for_mime(self.mime)

    def __str__(self):
        return self.name.encode('utf-8')
