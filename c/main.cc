#include <cstdio>

#include "nix/nix_api_expr.h"
#include "nix/nix_api_util.h"
#include "nix/nix_api_value.h"

void printf_string_cb(const char * s, unsigned int n, void *user_data)
{
    printf("%s\n", s);
}

int main() {
   nix_c_context* ctx = nix_c_context_create();

   nix_libexpr_init(ctx);
   if (nix_err_code(ctx) != NIX_OK) {
      printf("error: %s\n", nix_err_msg(nullptr, ctx, nullptr));
      return 1;
   }

   //Store* store = nix_store_open(nullptr, "dummy", nullptr);
   /* Store* store = nix_store_open(nullptr, "daemon", nullptr); */
   Store* store = nix_store_open(ctx, "", nullptr);
   if (nix_err_code(ctx) != NIX_OK) {
      printf("error: %s\n", nix_err_msg(nullptr, ctx, nullptr));
      return 1;
   }

   EvalState* state = nix_state_create(ctx, nullptr, store); // empty nix path
   if (nix_err_code(ctx) != NIX_OK) {
      printf("error: %s\n", nix_err_msg(nullptr, ctx, nullptr));
      return 1;
   }

   nix_value *value = nix_alloc_value(ctx, state);
   if (nix_err_code(ctx) != NIX_OK) {
      printf("error: %s\n", nix_err_msg(nullptr, ctx, nullptr));
      return 1;
   }

   nix_expr_eval_from_string(ctx, state, "builtins.nixVersion", ".", value);
   if (nix_err_code(ctx) != NIX_OK) {
      printf("error: %s\n", nix_err_msg(nullptr, ctx, nullptr));
      return 1;
   }

   nix_value_force(ctx, state, value);
   if (nix_err_code(ctx) != NIX_OK) {
      printf("error: %s\n", nix_err_msg(nullptr, ctx, nullptr));
      return 1;
   }

   printf("nix version: ");
   nix_get_string(ctx, value, printf_string_cb, nullptr);
   printf("\n");

   nix_gc_decref(ctx, value);
   if (nix_err_code(ctx) != NIX_OK) {
      printf("error: %s\n", nix_err_msg(nullptr, ctx, nullptr));
      return 1;
   }

   nix_state_free(state);
   nix_store_free(store);
   return 0;
}
