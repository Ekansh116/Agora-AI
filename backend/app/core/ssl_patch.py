import os
import ssl
import sys

disable_ssl = os.getenv("DISABLE_SSL_VERIFY", "false").lower() in ("true", "1", "yes")

if disable_ssl:
    sys.stderr.write("[SECURITY WARNING] DISABLE_SSL_VERIFY is set to true. Disabling TLS certificate validation.\n")
    
    # 1. Patch ssl.create_default_context globally to ignore validation
    try:
        original_create_default_context = ssl.create_default_context
        def patched_create_default_context(*args, **kwargs):
            context = original_create_default_context(*args, **kwargs)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context
        ssl.create_default_context = patched_create_default_context
    except Exception as e:
        sys.stderr.write(f"Warning: ssl.create_default_context patch failed: {e}\n")

    # 2. Disable urllib standard SSL checks globally
    try:
        ssl._create_default_https_context = ssl._create_unverified_context
    except Exception as e:
        sys.stderr.write(f"Warning: ssl context override failed: {e}\n")

    # 3. Disable urllib3 PoolManager and HTTPSConnectionPool validation
    try:
        import urllib3
        urllib3.disable_warnings()
        
        original_pool_init = urllib3.PoolManager.__init__
        def patched_pool_init(self, *args, **kwargs):
            kwargs['cert_reqs'] = 'CERT_NONE'
            original_pool_init(self, *args, **kwargs)
        urllib3.PoolManager.__init__ = patched_pool_init

        original_https_init = urllib3.connectionpool.HTTPSConnectionPool.__init__
        def patched_https_init(self, *args, **kwargs):
            kwargs['cert_reqs'] = 'CERT_NONE'
            if 'cert_reqs' in kwargs:
                kwargs['cert_reqs'] = 'CERT_NONE'
            original_https_init(self, *args, **kwargs)
        urllib3.connectionpool.HTTPSConnectionPool.__init__ = patched_https_init
    except Exception as e:
        sys.stderr.write(f"Warning: urllib3 patching failed: {e}\n")

    # 4. Disable requests SSL checks
    try:
        import requests
        from requests.packages.urllib3.exceptions import InsecureRequestWarning
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        
        original_request = requests.Session.request
        def patched_request(self, *args, **kwargs):
            kwargs['verify'] = False
            return original_request(self, *args, **kwargs)
        requests.Session.request = patched_request
    except Exception as e:
        sys.stderr.write(f"Warning: requests monkeypatch failed: {e}\n")

    # 5. Environment variables override
    os.environ["CURL_CA_BUNDLE"] = ""
    os.environ["REQUESTS_CA_BUNDLE"] = ""
    os.environ["HF_HUB_DISABLE_SSL_VERIFY"] = "1"
    os.environ["HF_HUB_DISABLE_SSL_VERIFICATION"] = "1"
    os.environ["SSL_CERT_FILE"] = ""
    os.environ["SSL_CERT_DIR"] = ""

