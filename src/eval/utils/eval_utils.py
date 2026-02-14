"""Utility functions for the evaluation module."""

from agents import get_model_config


def get_optimizer_config() -> dict:
  """Returns the optimizer config from the config file."""
  return get_model_config()["optimizer"]
