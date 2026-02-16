#!/usr/bin/env python3

import os
from ctypes import *

import pkgconfig

NIX_LIB_PATH = pkgconfig.variables("nix-expr-c")["libdir"]

exprc = cdll.LoadLibrary(f"{NIX_LIB_PATH}/libnixexprc.so")


if __name__ == "__main__":
  # nix_c_context* ctx = nix_c_context_create();
  ctx = c_void_p(exprc.nix_c_context_create())
  # nix_libexpr_init(ctx);
  exprc.nix_libexpr_init(ctx);
  # Store* store = nix_store_open(ctx, "", nullptr);
  store = c_void_p(exprc.nix_store_open(ctx, "", None));
  # EvalState* state = nix_state_create(ctx, nullptr, store); // empty nix path
  state = c_void_p(exprc.nix_state_create(ctx, None, store));
  # nix_value *value = nix_alloc_value(ctx, state);
  value = c_void_p(exprc.nix_alloc_value(ctx, state));
  # nix_expr_eval_from_string(ctx, state, "builtins.nixVersion", ".", value);
  exprc.nix_expr_eval_from_string(ctx, state, c_wchar_p("builtins.nixVersion"), c_wchar_p("."), value);

  exprc.nix_value_force(ctx, state, value);
  print(value)
  # printf("nix version: ");
  # nix_gc_decref(ctx, value);

  # nix_state_free(state);
  # nix_store_free(store);
  # return 0;
