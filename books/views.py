from django.http.response import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, render
from django.contrib.auth.decorators import login_required
from books.models import Book, Topic, PRIVACY_CHOICES, History
from books.forms import BookForm, TopicForm
from django.core.exceptions import ObjectDoesNotExist
from micro_admin.models import User
from django.db.models import Q
import json
import datetime


@login_required
def books(request):
    books = Book.objects.all()
    return render(request, "docs/books/list_of_books.html", {"books": books})


@login_required
def create_book(request):
    if request.user.is_superuser:
        if request.method == "POST":
            book_form = BookForm(request.POST)

            if book_form.is_valid():
                book = book_form.save()
                book.status = "Waiting"
                book.authors.add(request.user)
                book.save()
                data = {"error": False, "response": "Book created"}

            else:
                data = {"error": True, "response": book_form.errors}

            return HttpResponse(json.dumps(data))

        users = User.objects.all()
        return render_to_response("docs/books/create_book.html", {"users": users, "privacy_choices": PRIVACY_CHOICES})

    return render_to_response("admin/accessdenied.html")


@login_required
def view_book(request, slug):
    book = Book.objects.get(slug=slug)
    return render(request, "docs/books/book_detail.html", {"book": book})


@login_required
def view_book_topics(request, slug):
    book = Book.objects.get(slug = slug)

    topics = Topic.objects.filter(book = book, parent__isnull = True, shadow__isnull = True)

    return render(request, "docs/topics/list_of_book_topics.html",{"book" : book, "topics" : topics})


@login_required
def create_topic(request, slug):
    book = Book.objects.get(slug = slug)
    
    if request.method == "POST":
        topic_form = TopicForm(request.POST)
        
        if topic_form.is_valid():
            topic = topic_form.save()
            topic.status = "Waiting"
            topic.authors.add(request.user)
            
            try:
                Book.objects.get(slug = slug, authors__in = [request.user])

            except ObjectDoesNotExist:
                book.authors.add(request.user)
                book.save()

            if request.POST.get("topic") == "sub-topic":
                topic.parent = Topic.objects.get(id = request.POST.get("topic_id"))

            topic.save()

            data = {"error" : False, "response" : "Topic created"}

        else:
            data = {"error" : True, "response" : topic_form.errors}
        
        return HttpResponse(json.dumps(data))

    return render_to_response("docs/topics/create_topic.html", {"book" : book, "topic" : request.GET.get("topic"), "topic_id" : request.GET.get("topic_id")})


@login_required
def view_topic(request, book_slug, topic_slug):
    book = Book.objects.get(slug = book_slug)
    topic = Topic.objects.get(slug = topic_slug)
    topic_shadows = Topic.objects.filter(shadow=topic.id)
    return render_to_response("docs/topics/topic_detail.html", {"book" : book, "topic" : topic, "topic_shadows":topic_shadows})


@login_required
def view_subtopic(request, book_slug, topic_slug, subtopic_slug):
    book = Book.objects.get(slug = book_slug)
    topic = Topic.objects.get(slug = topic_slug)
    subtopic = Topic.objects.get(slug = subtopic_slug)
    subtopic_shadows = Topic.objects.filter(shadow=subtopic.id)
    return render_to_response("docs/topics/topic_detail.html", {"book" : book, "topic":topic, "subtopic" : subtopic, "subtopic_shadows":subtopic_shadows})


@login_required
def view_book_doc(request, slug):
    book = Book.objects.get(slug = slug)
    topics = Topic.objects.filter(book = book, parent__isnull = True, shadow__isnull = True)
    return render(request, "docs/books/book_document.html",{"book" : book, "topics" : topics})


@login_required
def edit_topic(request, book_slug, topic_slug):
    book = Book.objects.get(slug = book_slug)
    topic = Topic.objects.get(slug = topic_slug)

    if request.method == "POST":
        topic_form = TopicForm(request.POST)
        
        if topic_form.is_valid():
            new_topic = topic_form.save()
            new_topic.status = "Waiting"
            new_topic.authors.add(request.user)
            
            try:
                Book.objects.get(slug = book_slug, authors__in = [request.user])

            except ObjectDoesNotExist:
                book.authors.add(request.user)
                book.save()

            try:
                Topic.objects.get(slug = topic_slug, authors__in = [request.user])

            except ObjectDoesNotExist:
                topic.authors.add(request.user)
                topic.save()

            if topic.parent:
                new_topic.parent = topic.parent

            new_topic.shadow = topic

            new_topic.save()

            data = {"error" : False, "response" : "Topic has been edited Successfully"}

        else:
            data = {"error" : True, "response" : topic_form.errors}
        
        return HttpResponse(json.dumps(data))

    return render_to_response("docs/topics/edit_topic.html", {"book" : book, "topic" : topic})


@login_required
def approve_topic(request, book_slug, topic_slug):

    book = Book.objects.get(slug = book_slug)
    
    if request.user.is_superuser or book.admin == request.user:
        
        topic = Topic.objects.get(slug = topic_slug)

        if topic.shadow:
            history = History.objects.create(topic = topic.shadow, title = topic.shadow.title, 
                            content = topic.shadow.content)

            history.slug = history.create_slug(topic.shadow.slug)
            history.save()

            topic.shadow.title = topic.title
            topic.shadow.status = "Approved"
            topic.shadow.content = topic.content
            topic.updated_on = datetime.datetime.now()
            topic.shadow.save()

            topic.delete()

            data = {"topic_slug": topic.shadow.slug, "response" : "Approved Successfully"}
        else:
            topic.status = "Approved"
            topic.save()

            data = {"response" : "Approved Successfully"}

    else:
        data = {"response" : "You don't have the permission to Approve."}
    
    return HttpResponse(json.dumps(data))


@login_required
def reject_topic(request, book_slug, topic_slug):

    book = Book.objects.get(slug = book_slug)
    
    if request.user.is_superuser or book.admin == request.user:
        
        topic = Topic.objects.get(slug = topic_slug)
        topic.status = "Rejected"
        topic.save()
        data = {"response" : "Rejected Successfully"}

    else:
        data = {"response" : "You don't have the permission to Reject."}
    
    return HttpResponse(json.dumps(data))


@login_required
def delete_topic(request, book_slug, topic_slug):
    book = Book.objects.get(slug = book_slug)
    
    if request.user.is_superuser or book.admin == request.user:
        
        topic = Topic.objects.get(slug = topic_slug)
        topic.delete()
        data = {"response" : "Deleted Successfully"}

    else:
        data = {"response" : "You don't have the permission to Delete."}
    
    return HttpResponse(json.dumps(data))


@login_required
def edit_book(request, slug):
    book = Book.objects.get(slug = slug)
    if request.user.is_superuser or book.admin == request.user:

        if request.method == "POST":
            book_form = BookForm(request.POST, instance = book)
            
            if book_form.is_valid():
                book = book_form.save()
                book.status = "Waiting"
                book.authors.add(request.user)
                book.save()
                data = {"error" : False, "response" : "Book has been edited Successfully."}
            
            else:
                data = {"error" : True, "response" : book_form.errors}
            
            return HttpResponse(json.dumps(data))

        users = User.objects.all()
        return render_to_response("docs/books/edit_book.html", {"book": book, "users": users, "privacy_choices":PRIVACY_CHOICES})

    return render_to_response("admin/accessdenied.html")


@login_required
def approve_book(request, slug):

    if request.user.is_superuser:
        
        book = Book.objects.get(slug = slug)
        book.status = "Approved"
        book.save()

        return render(request, "docs/books/book_detail.html", {"book" : book})
    
    else:
        return render_to_response("admin/accessdenied.html")


@login_required
def reject_book(request, slug):

    if request.user.is_superuser:
        
        book = Book.objects.get(slug = slug)
        book.status = "Rejected"
        book.save()
        return render(request, "docs/books/book_detail.html", {"book" : book})
    
    else:
        return render_to_response("admin/accessdenied.html")


@login_required
def delete_book(request, slug):

    if request.user.is_superuser:
        book = Book.objects.get(slug = slug)
        book.delete()
        return HttpResponseRedirect('/docs/books/')
    
    else:
        return render_to_response("admin/accessdenied.html")


def book_list(request):
    books = Book.objects.filter(privacy="public",status="Approved")
    return render_to_response("docs/books.html",{"books":books})


def book_info(request, slug):
    book = Book.objects.get(slug=slug)
    parent_topics = Topic.objects.filter(Q(book_id=book.id) & Q(parent=None) & Q(status="Approved") & Q(shadow_id=None))
    return render_to_response("docs/book_topics.html",{"book":book,"parent_topics":parent_topics})


def topic_info(request, book_slug, topic_slug):
    book = Book.objects.get(slug=book_slug)
    topic = Topic.objects.get(slug=topic_slug)
    parent_topics = Topic.objects.filter(Q(book_id=book.id) & Q(parent=None) & Q(status="Approved") & Q(shadow_id=None))
    return render_to_response("docs/book_topics.html",{"book":book,"parent_topics":parent_topics,"topic":topic})


def subtopic_info(request, book_slug, subtopic_slug):
    book = Book.objects.get(slug=book_slug)
    subtopic = Topic.objects.get(slug=subtopic_slug)
    parent_topics = Topic.objects.filter(Q(book_id=book.id) & Q(parent=None) & Q(status="Approved") & Q(shadow_id=None))
    return render_to_response("docs/book_topics.html",{"book":book,"parent_topics":parent_topics,"subtopic":subtopic})
