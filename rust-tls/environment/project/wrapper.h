#ifndef WRAPPER_H
#define WRAPPER_H

#include <unistd.h>
#include <stdint.h>
#include <stddef.h>
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/bio.h>
#include <openssl/evp.h>

// SSL/TLS functions - these force libssl.so linkage
typedef struct ssl_st SSL;
typedef struct ssl_ctx_st SSL_CTX;
typedef struct ssl_method_st SSL_METHOD;

// BUG: Missing const qualifier - will cause type mismatch
SSL_METHOD* TLS_client_method(void);

SSL_CTX* SSL_CTX_new(SSL_METHOD* method);
void SSL_CTX_free(SSL_CTX* ctx);

// BUG: Missing error return value documentation
int SSL_CTX_set_default_verify_paths(SSL_CTX* ctx);

SSL* SSL_new(SSL_CTX* ctx);
void SSL_free(SSL* ssl);

// BUG: Missing BIO type declaration
typedef struct bio_st BIO;
BIO* BIO_new_socket(int sock, int close_flag);

int SSL_set_bio(SSL* ssl, BIO* rbio, BIO* wbio);
int SSL_set_connect_state(SSL* ssl);

// BUG: Missing const qualifier on hostname
int SSL_set_tlsext_host_name(SSL* ssl, const char* name);

int SSL_connect(SSL* ssl);
int SSL_get_error(SSL* ssl, int ret);

// BUG: Missing size_t parameter type
int SSL_read(SSL* ssl, void* buf, int num);
int SSL_write(SSL* ssl, const void* buf, int num);

const char* SSL_get_version(SSL* ssl);

// Error handling
unsigned long ERR_get_error(void);
void ERR_error_string_n(unsigned long e, char* buf, size_t len);

// BIO functions
int BIO_read(BIO* bio, void* buf, int len);
int BIO_write(BIO* bio, const void* buf, int len);
void BIO_free_all(BIO* bio);

#endif // WRAPPER_H
