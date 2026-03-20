# SmartShield

AI-powered income protection for gig workers

---

## Overview

SmartShield is a simple platform designed to protect gig workers from losing income due to things they can’t control, like bad weather or pollution. It uses AI to estimate risk, adjust weekly premiums, and automatically trigger payouts when disruptions happen.

---

## The Problem

Delivery partners often lose part of their earnings when conditions are unfavorable. Right now, there’s no easy way for them to recover that lost income.

---

## Our Approach

SmartShield offers a lightweight insurance system that works on a weekly model. It monitors external conditions and, when a disruption meets certain criteria, it automatically processes a claim. There’s no need for the user to apply manually.

---

## Key Features

* Risk prediction based on location and conditions
* Dynamic weekly premium calculation
* Automatic claim triggering
* Basic fraud detection
* Simple dashboard for tracking coverage and payouts

---

## How It Works

1. The user signs up and provides basic details
2. The system calculates a weekly premium
3. External data (like weather) is monitored
4. If a disruption occurs, a claim is triggered
5. The system verifies the claim and processes a payout

---

## Tech Stack

* Frontend: React or basic web technologies
* Backend: Node.js or Flask
* AI/ML: Python (Scikit-learn)
* Database: MongoDB or MySQL

---

## Team

A team of three handling frontend, backend, and AI/ML.

---

## Final Note

SmartShield focuses on one goal: making sure gig workers have a basic financial safety net when unexpected disruptions affect their income.





## Adversarial Defense & Anti-Spoofing Strategy

SmartShield protects against GPS spoofing and coordinated fraud using AI-driven, multi-layered checks beyond just location data.

Differentiation

Cross-checks movement, device integrity, and environment. Real workers show natural behavior; spoofers don’t.

Data Used

Motion sensors (accelerometer, gyroscope)

Device health (mock locations, rooted devices)

Network signals & history

Weather APIs and optional OTPs

Fraud & Attack Detection

Rule-based filters for impossible activity

ML models and anomaly detection

Coordinated attack monitoring (group patterns)

Workflow

Collect signals

Filter impossible data

Analyze with ML

Scan for groups

Decide auto/manual review

UX Balance

Flag suspicious claims instead of rejecting immediately

Tolerate minor GPS or network inconsistencies

High-risk cases reviewed manually

Summary

SmartShield reduces fraud while keeping the system fair and seamless for genuine users.
