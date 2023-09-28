# from datetime import timezone
from django.utils import timezone
from django.shortcuts import redirect, get_object_or_404
from django.db.models import Q
from django.db.models import Count
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    DetailView, CreateView, ListView, UpdateView, DeleteView
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User

from .forms import CommentForm, PostForm
from .models import Post, Category, Comment

MAX_POSTS = 10


class PostFormMixin:
    model = Post
    template_name = 'blog/create.html'
    form_class = PostForm
    pk_url_kwarg = 'post_id'

    def dispatch(self, request, *args, **kwargs):
        post = get_object_or_404(Post, pk=self.kwargs['post_id'])
        if post.author != self.request.user:
            return redirect(
                'blog:post_detail',
                post_id=self.kwargs['post_id']
            )
        return super().dispatch(request, *args, **kwargs)


class PostQuerySet:
    pk_url_kwarg = 'post_id'

    def get_queryset(self):
        return Post.objects.select_related(
            'author', 'location', 'category').filter(
            is_published=True,
            category__is_published=True,
            pub_date__lte=timezone.now()
        ).order_by('-pub_date').all()


class PostListView(PostQuerySet, ListView):
    paginate_by = MAX_POSTS
    template_name = 'blog/index.html'

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.annotate(comment_count=Count('comments'))


class PostDetailView(LoginRequiredMixin, PostQuerySet, DetailView):
    model = Post
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'post_id'

    def get_context_data(self, **kwargs):
        return dict(
            **super().get_context_data(**kwargs),
            form=CommentForm(),
            comments=self.object.comments.all()
        )

    def get_object(self, queryset=None):
        post = Post.objects
        if (self.request.user.is_authenticated):
            post = Post.objects.all(
            ).filter(Q(is_published=True,
                       category__is_published=True,
                       pub_date__lt=timezone.now()) | Q(
                           author=self.request.user))
            return get_object_or_404(post, pk=self.kwargs['post_id'])


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'blog:profile',
            args=[self.request.user.username]
        )


class PostUpdateView(PostFormMixin, UpdateView):
    def get_success_url(self):
        return reverse('blog:post_detail',
                       args=[self.kwargs['post_id']])


class PostDeleteView(PostFormMixin, DeleteView):
    def get_success_url(self):
        return reverse('blog:profile',
                       args=[self.request.user.username])


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    template_name = 'blog/user.html'
    fields = ('username', 'first_name', 'last_name', 'email')

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return reverse_lazy(
            'blog:profile',
            kwargs={'username': self.request.user.username}
        )


class ProfileListView(PostQuerySet, ListView):
    paginate_by = MAX_POSTS
    template_name = 'blog/profile.html'
    model = Post

    def get_object(self):
        return get_object_or_404(User, username=self.kwargs['username'])

    def get_queryset(self):
        queryset = Post.objects
        self.profile = get_object_or_404(User,
                                         username=self.kwargs['username'])

        queryset = queryset.filter(
            author=self.profile
            # не работает сортировка если задать ordering на уровне модели.
            # помоги:)
        ).annotate(comment_count=Count('comments')).order_by('-pub_date')
        if self.request.user != self.profile:
            queryset = super().get_queryset().annotate(
                comment_count=Count('comments'))

        return queryset

    def get_context_data(self, **kwargs):
        return dict(
            **super().get_context_data(**kwargs),
            profile=self.get_object()
        )


class CommentMixin(LoginRequiredMixin):
    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def get_success_url(self):
        return reverse('blog:post_detail', args=[self.kwargs['post_id']])

    def dispatch(self, request, *args, **kwargs):
        coment = get_object_or_404(Comment, id=self.kwargs['comment_id'])
        if coment.author != self.request.user:
            return redirect('blog:post_detail',
                            post_id=self.kwargs['post_id']
                            )
        return super().dispatch(request, *args, **kwargs)


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    template_name = 'blog/comment.html'
    form_class = CommentForm

    def get_context_data(self, **kwargs):
        return dict(**super().get_context_data(**kwargs), form=CommentForm())

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.post = get_object_or_404(Post, pk=self.kwargs['post_id'])
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('blog:post_detail', args=[self.kwargs['post_id']])


class CommentUpdateView(CommentMixin, UpdateView):
    form_class = CommentForm


class CommentDeleteView(CommentMixin, DeleteView):
    pass


class PostCategoryView(PostQuerySet, ListView):
    template_name = 'blog/category.html'
    context_object_name = 'post_list'
    paginate_by = MAX_POSTS
    category = None

    def get_queryset(self):
        category_slug = self.kwargs['category_slug']
        self.category = get_object_or_404(
            Category,
            slug=self.kwargs['category_slug'],
            is_published=True
        )
        return super().get_queryset().filter(
            category__slug=category_slug
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context
