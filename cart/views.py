from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
import json
from .models import Cart, CartItem
from products.models import *
from firebase.firebase_auth import firebase_login_required
from django.http import JsonResponse
from firebase.firebase_auth import firebase_login_required



# Helper to get Firebase UID from headers
def get_firebase_uid(request):
    return request.headers.get('X-Firebase-UID')


def get_or_create_cart(request):
    """Get or create cart using Firebase UID set by the decorator"""
    firebase_uid = request.firebase_user.get('uid')  # ✅ Extract UID from token
    cart, created = Cart.objects.get_or_create(firebase_uid=firebase_uid)
    return cart



@csrf_exempt
@firebase_login_required
@require_GET
def cart_api(request):
    try:
        cart = get_or_create_cart(request)
        items = CartItem.objects.filter(cart=cart).select_related('product', 'size')

        cart_items = []
        for item in items:
            image_url = None
            color_name = None

            try:
                product_color = ProductColor.objects.filter(product=item.product, color=item.color).first()

                if product_color:
                    color_name = product_color.color.name if hasattr(product_color.color, 'name') else None
                    first_image = product_color.images.first()
                    if first_image and hasattr(first_image, 'image') and first_image.image:
                        image_url = request.build_absolute_uri(first_image.image.url)
            except Exception as e:
                print(f"Image or color error: {e}")

            cart_items.append({
                'id': item.id,
                'product_id': item.product.id,
                'name': item.product.name,
                'price': float(item.price),
                'quantity': item.quantity,
                'size_id': item.size.id,
                'size_name': item.size.name,
                'image': image_url,
                'color': color_name,
                'color_id': item.color.id if item.color else None,  # ✅ Add this
            })

        return JsonResponse({
            'status': 'success',
            'items': cart_items,
            'total': float(cart.total),
            'item_count': cart.item_count,
            'csrf_token': get_token(request)
        })

    except Exception as e:
        import traceback
        print("Cart API Error:\n", traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@firebase_login_required
@require_POST
def add_to_cart(request, product_id):
    try:
        cart = get_or_create_cart(request)
        data = json.loads(request.body)
        size_id = data.get('size_id')
        color_id = data.get('color_id')
        quantity = int(data.get('quantity', 1))

        if not size_id:
            return JsonResponse({'status': 'error', 'message': 'Size is required'}, status=400)

        product = Products.objects.get(id=product_id)
        size = Size.objects.get(id=size_id)

        # ✅ Only define color if color_id is provided
        color = None
        if color_id:
            color = Color.objects.get(id=color_id)

        # ✅ Use color in get_or_create
        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            size=size,
            color=color,
            defaults={'quantity': quantity, 'price': product.currentprice}
        )

        if not created:
            item.quantity += quantity
            item.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Item added to cart',
            'item_count': cart.item_count,
            'total': float(cart.total)
        })

    except Products.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Product not found'}, status=404)
    except Size.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Size not found'}, status=404)
    except Color.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Color not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)



@csrf_exempt
@firebase_login_required
@require_POST
def update_cart_item(request, product_id):
    try:
        cart = get_or_create_cart(request)
        data = json.loads(request.body)
        quantity = int(data.get('quantity', 1))
        size_id = data.get('size_id')
        color_id = data.get('color_id')

        if not size_id or not color_id:
            return JsonResponse({'status': 'error', 'message': 'Size and color are required'}, status=400)

        product = Products.objects.get(id=product_id)
        size = Size.objects.get(id=size_id)
        color = Color.objects.get(id=color_id)

        if quantity < 1:
            CartItem.objects.filter(cart=cart, product=product, size=size, color=color).delete()
        else:
            item = CartItem.objects.get(cart=cart, product=product, size=size, color=color)
            item.quantity = quantity
            item.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Cart updated',
            'items': [{
                'id': item.id,
                'product_id': item.product.id,
                'quantity': item.quantity,
                'price': float(item.price)
            } for item in cart.items.all()],
            'total': float(cart.total),
            'item_count': cart.item_count
        })

    except CartItem.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Cart item not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@firebase_login_required
@require_POST
def remove_cart_item(request, product_id):
    try:
        cart = get_or_create_cart(request)
        data = json.loads(request.body)
        size_id = data.get('size_id')
        color_id = data.get('color_id')

        if not size_id or not color_id:
            return JsonResponse({'status': 'error', 'message': 'Size and color are required'}, status=400)

        product = Products.objects.get(id=product_id)
        size = Size.objects.get(id=size_id)
        color = Color.objects.get(id=color_id)

        CartItem.objects.filter(cart=cart, product=product, size=size, color=color).delete()

        return JsonResponse({
            'status': 'success',
            'message': 'Item removed',
            'total': float(cart.total),
            'item_count': cart.item_count
        })

    except Products.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Product not found'}, status=404)
    except Size.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Size not found'}, status=404)
    except Color.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Color not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@firebase_login_required
def my_secure_view(request):
    firebase_user = request.firebase_user
    return JsonResponse({"message": "Hello, Firebase User!", "uid": firebase_user["uid"]})
