from django.shortcuts import render, HttpResponse

# Create your views here.

def index(request):
    return render(request, "index.html")

def about(request):
    return HttpResponse("This is about page")


def chats(request):
    return HttpResponse("all the chats here")


def groups(request):
    return HttpResponse("Featured groups here")
