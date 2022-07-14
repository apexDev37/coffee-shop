import json
from flask import request, _request_ctx_stack
from functools import wraps
from jose import jwt
from urllib.request import urlopen

# -------------------------AUTH0 Credentials------------------------- #

AUTH0_DOMAIN = 'euon-fsnd.us.auth0.com'
AUTH0_CLIENT_ID = 't8vEyvgObDTMEfI9AqMq2rTnpgGOH2Ia'
API_AUDIENCE = 'http://127.0.0.1:5000/api/v1/'
ALGORITHMS = ['RS256']


# -----------------------------AuthError----------------------------- #

'''
AuthError Exception
A standardized way to communicate auth failure modes
'''


class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code

# ----------------------------Auth Header---------------------------- #


'''
@DONE: implement get_token_auth_header() method
    it should attempt to get the header from the request
        it should raise an AuthError if no header is present
    it should attempt to split bearer and the token
        it should raise an AuthError if the header is malformed
    return the token part of the header
'''


def get_token_auth_header():
    # Verify auth header present
    auth_header = get_auth_header_or_401()
    auth_header_parts = auth_header.split(' ')

    # Verify auth header valid or raise AuthError
    handle_invalid_auth_header(auth_header_parts)

    # Handle response
    token = auth_header_parts[1]
    return token


def get_auth_header_or_401():
    # Handle auth header missing in request
    if 'Authorization' not in request.headers:
        raise AuthError({
            'code': 'missing_authorization_header',
            'description': 'Authorization header is required'}, 401)

    # Handle auth header data
    auth_header = request.headers['Authorization']
    return auth_header


def handle_invalid_auth_header(auth_header_parts):
    # Handle Bearer not in auth header
    if auth_header_parts[0].lower() != 'bearer':
        error_desc = 'Authorization header must start with Bearer'
        raise_invalid_auth_header(error_desc)

    # Handle token absent in auth header
    elif len(auth_header_parts) == 1:
        error_desc = 'Authorization header must contain token'
        raise_invalid_auth_header(error_desc)

    # Handle violation of auth header format
    elif len(auth_header_parts) > 2:
        error_desc = 'Authorization header format not <Bearer token>'
        raise_invalid_auth_header(error_desc)


def raise_invalid_auth_header(error_desc):
    raise AuthError({
        'code': 'invalid_auth_header',
        'description': error_desc}, 401)


'''
@DONE: implement check_permissions(permission, payload) method
    @INPUTS
        permission: string permission (i.e. 'post:drink')
        payload: decoded jwt payload

    it should raise an AuthError if permissions are not included in the payload
        !!NOTE check your RBAC settings in Auth0
    it should raise an AuthError if the requested permission string is not
    in the payload permissions array return true otherwise
'''


def check_permissions(permission, payload):
    # Handle missing permission claims in JWT payload
    if 'permissions' not in payload:
        raise AuthError({
            'code': 'invalid_claims',
            'description': 'Permission claims not in JWT'}, 400)

    # Handle missing required permission
    if permission not in payload['permissions']:
        raise AuthError({
            'code': 'unauthorized',
            'description': 'Forbidden: Permission not found'}, 403)

    return True


'''
@DONE: implement verify_decode_jwt(token) method
    @INPUTS
        token: a json web token (string)

    it should be an Auth0 token with key id (kid)
    it should verify the token using Auth0 /.well-known/jwks.json
    it should decode the payload from the token
    it should validate the claims
    return the decoded payload

    !!NOTE urlopen has a common certificate error described here:
    https://stackoverflow.com/questions/50236117/scraping-ssl-certificate-verify-failed-error-for-http-en-wikipedia-org
'''


def verify_decode_jwt(token):
    # Retrieve public key from Auth0
    jsonurl = urlopen(f'https://{AUTH0_DOMAIN}/.well-known/jwks.json')
    jwks = json.loads(jsonurl.read())
    unverified_jwt_header = jwt.get_unverified_header(token)

    rsa_key = get_RSA_key_or_401(jwks, unverified_jwt_header)

    # Verify jwt and return jwt payload
    if rsa_key:
        jwt_payload = validate_jwt(rsa_key, token)
        return jwt_payload

    # Raise AuthError for missing key
    error_desc = 'Unable to find the appropriate key'
    raise_invalid_auth_header(error_desc)


def get_RSA_key_or_401(jwks, unverified_jwt_header):
    """
    Auth0 Boiler plate code to choose and format RSA key.
    """

    # Raise AuthError if kid is missing
    if 'kid' not in unverified_jwt_header:
        error_desc = 'Authorization header malformed'
        raise_invalid_auth_header(error_desc)

    # Choose and return RSA key
    for key in jwks['keys']:
        if key['kid'] == unverified_jwt_header['kid']:
            return {
                'kty': key['kty'],
                'kid': key['kid'],
                'use': key['use'],
                'n': key['n'],
                'e': key['e']
            }


def validate_jwt(rsa_key, token):
    try:
        payload = jwt.decode(
            token=token,
            key=rsa_key,
            algorithms=ALGORITHMS,
            audience=API_AUDIENCE,
            issuer=f'https://{AUTH0_DOMAIN}/'
        )

        return payload

    # Handle common exceptions and raise AuthError
    except jwt.ExpiredSignatureError:
        raise AuthError({
            'code': 'token_expired',
            'description': 'Token expired.'}, 401)
    except jwt.JWTClaimsError:
        raise AuthError({
            'code': 'invalid_claims',
            'description': 'Incorrect claims.' +
            'Please, check the audience and issuer.'}, 401)
    except Exception:
        raise AuthError({
            'code': 'invalid_header',
            'description': 'Unable to parse authentication token.'}, 400)


'''
@TODO implement @requires_auth(permission) decorator method
    @INPUTS
        permission: string permission (i.e. 'post:drink')

    it should use the get_token_auth_header method to get the token
    it should use the verify_decode_jwt method to decode the jwt
    it should use the check_permissions method validate claims and
    check the requested permission return the decorator which passes
    the decoded payload to the decorated method
'''


def requires_auth(permission=''):
    def requires_auth_decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = get_token_auth_header()
            payload = verify_decode_jwt(token)
            check_permissions(permission, payload)
            return f(payload, *args, **kwargs)

        return wrapper
    return requires_auth_decorator
