# Project Brief

## Goal
Build a Turkish conversational AI module for a waiter robot that supports menu-aware,
polite, and safety-conscious text dialogue. The current project also includes a
supervised fine-tuning data pipeline for later model work targeting local deployment
on Jetson Orin NX.

## Current Product Direction

### Track 1: Deterministic Baseline (Complete and Measurable)
- Rule-based dialogue manager with Turkish intent matching
- Structured menu and restaurant data from YAML
- Order state management for add, remove, clear, update, and summarize flows
- Safe handling for allergies, unknown items, and off-topic requests
- Interactive CLI demo
- Automated evaluation runner with benchmark coverage

### Track 2: Fine-Tuning Preparation (Foundation Complete, Training Not Started)
- Structured seed dialogue dataset in YAML
- Dataset validator with allowed-intent enforcement
- SFT dataset builder for train/validation JSONL generation
- Evaluation cases for intent, safety, and order-flow coverage
- Later: LoRA/QLoRA fine-tuning of a small local model
- Later: inference on Jetson Orin NX

## Out of Current Scope
- Robot navigation, ROS 2, Nav2, SLAM, or motor control
- Perception, camera, LiDAR, or face recognition
- Payments or production restaurant management systems
- External LLM providers

## Success Criteria
- Greets customers politely in Turkish
- Answers menu questions without inventing items or allergens
- Takes and summarizes simple orders clearly
- Handles allergy-related questions cautiously
- Keeps the codebase testable, deterministic, and easy to extend later
