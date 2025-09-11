import re, json, os
from django.core.cache import cache
from django.conf import settings
from fuzzywuzzy import process
from django.http import JsonResponse
from customer.models import Customer
from invoice.models import Invoice
from inventory.models import Product, ProductVariant


# Precompiled regex for speed
TOKENIZER = re.compile(r"[a-zA-Z0-9]+")


def get_related_words(query, list_of_words):
    if not query or len(query) < 2 or not list_of_words:
        return []

    if not isinstance(list_of_words, list):
        return []

    list_of_words = list(set(list_of_words))

    fuzzy_matches = process.extract(query.lower(), list_of_words, limit=10)

    # Filter matches with score > 60 and return only words
    suggestions = []
    seen_words = set()
    for word, score in fuzzy_matches:
        if score > 60 and word not in seen_words:
            suggestions.append(word)
            seen_words.add(word)
            if len(suggestions) >= 5:
                break

    return suggestions


def get_search_words(
    query, model, fields, cache_key, cache_timeout=3600, use_file_cache=False
):
    """
    Generic helper to build/search word lists from any model fields.
    Uses Django cache with optional file-based fallback.
    Returns a list of unique lowercase words (up to max_words).
    """
    # File path (if enabled)
    cache_file = None
    if use_file_cache:
        cache_dir = os.path.join(settings.BASE_DIR, "cache_files")
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, f"{cache_key}.json")

    # Try Django cache first
    searchable_items = cache.get(cache_key)
    if searchable_items is not None:
        return get_related_words(query, searchable_items)

    # Try file cache fallback
    if cache_file and os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            searchable_items = json.load(f)
    else:
        # Build from DB
        queryset = model.objects.values_list(*fields).iterator()
        all_words = set()

        for row in queryset:
            for field in row:
                if field:
                    tokens = TOKENIZER.findall(str(field).lower())
                    all_words.update(tokens)

        # Trim to max_words
        searchable_items = list(all_words)

        # Save to file if enabled
        if cache_file:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(searchable_items, f)
    # Save to Django cache
    cache.set(cache_key, searchable_items, cache_timeout)

    suggestions = get_related_words(query, searchable_items)

    # Return the suggestions list, not JsonResponse
    return suggestions


def customer_all_suggestions(request):
    query = request.GET.get("q", "").strip()

    if not query or len(query) < 2:
        return JsonResponse({"success": True, "data": []})

    suggestions = get_search_words(
        query=query,
        model=Customer,
        fields=("name", "phone_number", "email", "address"),
        cache_key="customer_search_words",
        cache_timeout=3600,
        use_file_cache=True,
    )

    return JsonResponse({"success": True, "data": suggestions})


def invoice_all_suggestions(request):
    query = request.GET.get("q", "").strip()

    if not query or len(query) < 2:
        return JsonResponse({"success": True, "data": []})

    suggestions = get_search_words(
        query=query,
        model=Invoice,
        fields=("invoice_number", "customer__name", "customer__phone_number", "notes"),
        cache_key="invoice_search_words",
        cache_timeout=3600,
        use_file_cache=True,
    )

    return JsonResponse({"success": True, "data": suggestions})


def product_all_suggestions(request):

    query = request.GET.get("q", "").strip()

    if not query or len(query) < 2:
        return JsonResponse({"success": True, "data": []})

    suggestions = get_search_words(
        query=query,
        model=Product,
        fields=("brand", "name", "category__name"),
        cache_key="product_search_words",
        cache_timeout=3600,
        use_file_cache=True,
    )

    return JsonResponse({"success": True, "data": suggestions})


def product_variant_all_suggestions(request):
    query = request.GET.get("q", "").strip()

    if not query or len(query) < 2:
        return JsonResponse({"success": True, "data": []})

    suggestions = get_search_words(
        query=query,
        model=ProductVariant,
        fields=("barcode", "product__name", "product__brand", "product__category__name"),
        cache_key="product_variant_search_words",
        cache_timeout=3600,
        use_file_cache=True,
    )

    return JsonResponse({"success": True, "data": suggestions})