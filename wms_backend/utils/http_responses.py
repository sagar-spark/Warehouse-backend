# Utils for HTTP Responses
import json
from django.http import HttpResponse

http_status = {
    "success": 200,
    "error": 404,
    "unauthorized": 401
}


def respond_success(response):
    return HttpResponse(json.dumps({"response": response}),
                        status=http_status["success"],
                        content_type="application/json",
                        )


def respond_error(response, status=400):
    return HttpResponse(json.dumps({"response": response}),
                        status=status,
                        content_type="application/json",
                        )


def respond_unauthorized(response):
    return HttpResponse(json.dumps({"response": response}),
                        status=http_status["unauthorized"],
                        content_type="application/json",
                        )

def get_frontend_domain(request):
    if request:
        origin = request.headers.get('Origin')
        return origin
    else:
        # Replace with your actual domain
        return 'https://localhost:8000'   
