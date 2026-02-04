# Cynestudy Assistance

**Cynestudy Assistance** is a production-grade, AI-powered study planning and assistance backend system designed to help students plan, execute, revise, and improve their studies efficiently. The system leverages deterministic planning logic combined with a controlled AI study assistant to provide a robust educational coordination platform.

Built with a focus on reliability and scalability, this backend serves as the core infrastructure for the Cynestudy ecosystem.

---

## Project Overview

Cynestudy Assistance addresses the complexity of long-term academic preparation by automating schedule management, revision cycles, and performance tracking. Unlike standard planners, it utilizes a sophisticated backend engine to dynamically adjust study plans based on user performance, ensuring strictly optimized learning paths.

The architecture emphasizes **Clean Architecture principles**, ensuring that business logic remains decoupled from external frameworks, resulting in a system that is testable, maintainable, and adaptable to changing requirements.

**Organization**: CYNERZA  
**Main Author**: LUCIFER  
**Ownership**: Designed, engineered, and maintained by the CYNERZA Organization.

---

## Key Features

### Study Planner Engine
A deterministic core that generates personalized study schedules based on exam timelines, syllabus coverage, and subject proficiency. It ensures balanced load distribution across weeks and months.

### Daily Task Execution System
Manages the granular execution of study plans. It tracks daily tasks, logs completion status, and handles carry-over logic for unfinished items, ensuring no topic is left behind.

### Smart Revision Engine
Implements evidence-based spaced repetition algorithms (1-3-7-21 interval logic). The system automatically schedules revision sessions for completed topics to maximize retention and minimize the forgetting curve.

### Progress & Analytics
Provides deep insights into student performance. This module aggregates data on study consistency, topic completion rates, and weak areas, offering actionable metrics for improvement.

### Notification & Reminder Logic
A centralized notification system that manages alerts for upcoming tasks, revision dues, and subscription statuses. It supports multi-channel delivery logic and strictly adhering to priority rules.

### Subscription & Feature Control
A robust access control module managing user tiers (Free, Pro, Smart Pack). It centrally enforces usage limits, feature access, and subscription lifecycles, ensuring strict adherence to monetization strategies.

### AI Study Assistant (Smart Pack)
A controlled, context-aware AI coach powered by Azure OpenAI. It provides educational guidance, concept explanations, and motivation without solving assignments or facilitating academic dishonesty. It features strict ethical guardrails and rate-limiting access.

---

## System Architecture Overview

The backend follows a **Feature-Based Clean Architecture**, prioritizing separation of concerns and scalability.

- **Domain Layer**: Contains enterprise business rules and entities.
- **Service Layer**: Orchestrates business logic and application flows.
- **Repository Layer**: Abstracts data access, enabling database agnosticism.
- **Interface Layer (Routers)**: Thin API endpoints responsible only for request/response handling.

**Core Code Quality Standards**:
- **Reusable**: Components are designed for modularity and reuse.
- **Readable**: Strict adherence to code style and documentation standards.
- **Maintainable**: Clear separation of concerns minimizes technical debt.
- **Secure**: Authentication, authorization, and valid input sanitization at every layer.
- **Scalable**: Stateless design and efficient database indexing support horizontal scaling.
- **Testable**: Dependency injection allows for rigorous unit and integration testing.
- **Reliable**: Comprehensive error handling and transaction management.

---

## Backend Module Breakdown

The system is organized into distinct functional modules:

| Module | Description |
|--------|-------------|
| **Core** | Fundamental utilities, database connections, configuration, and security handling. |
| **Auth** | User authentication, token management, and profile security. |
| **Study Plan** | Logic for syllabus mapping, schedule generation, and milestone setting. |
| **Execution** | Daily task tracking, status updates, and backlog management. |
| **Revision** | Spaced repetition logic and revision scheduling. |
| **Analytics** | Data aggregation and performance reporting services. |
| **Timeline** | Helper utilities for date calculations and schedule adjustments. |
| **Notifications** | Alert generation and delivery prioritization. |
| **Subscription** | Plan management, usage quotas, and feature gating. |
| **AI Assistant** | Advisory AI layer with ethical prompting and context injection. |

---

## Technology Stack

### Core Technologies
- **Language**: Python 3.11+
- **Framework**: FastAPI (Asynchronous Web Framework)
- **Database**: MongoDB (via Motor for async operations)
- **Caching**: Redis (Planned/Supported)
- **AI Integration**: Azure OpenAI Service

### Libraries & Tools
- **Pydantic v2**: Data validation and schema management.
- **PyJWT**: Secure token handling.
- **Passlib**: Password hashing (Argon2/Bcrypt).
- **Dotenv**: Environment configuration management.

---

## API Design Philosophy

The API is designed to be **RESTful, predictable, and secure**.

1.  **Resource-Oriented**: URLs represent resources (e.g., `/plans`, `/tasks`).
2.  **Standardized Responses**: All endpoints return a unified response structure (Success vs. Error).
3.  **Thin Controllers**: Routers delegate all logic to the Service layer.
4.  **Stateless**: No client context is stored in memory; complete reliance on token-based authentication.
5.  **Strict Validation**: Input data is rigorously validated against Pydantic schemas before processing.

---

## AI Usage & Ethical Guidelines

The AI Study Assistant is engineered as a **support tool**, not a replacement for student effort.

- **Advisory Role**: The AI provides guidance, explanations, and strategies.
- **Academic Integrity**: The system explicitly blocks requests to solve assignments, write essays, or predict exam questions.
- **Context Awareness**: Responses are personalized based on the user's specific study profile and weak areas.
- **Transparency**: All AI interactions are logged for auditing and usage tracking.

---

## Security & Access Control

Security is integrated into every layer of the application:
- **Authentication**: JWT (JSON Web Tokens) with strict expiration policies.
- **Authorization**: Role-based (RBAC) and Plan-based access control.
- **Data Protection**: Sensitive data is hashed; communications are encrypted via TLS (in deployment).
- **Rate Limiting**: API endpoints, particularly AI services, enforce usage quotas to prevent abuse.

---

## Project Structure

```
/app
├── api
│   └── v1              # Versioned API Routers
├── core
│   ├── config          # Environment & Application Settings
│   ├── database        # Database Connection & Base Models
│   ├── security        # Auth Utilities & Password Hashing
│   └── ai              # Abstracted AI Clients
├── modules
│   ├── auth            # User Management
│   ├── study_plan      # Planning Engine
│   ├── execution       # Task Tracking
│   ├── revision        # Smart Revision
│   ├── analytics       # Progress Reports
│   ├── notifications   # Alert System
│   ├── subscription    # Plan Control
│   └── ai_assistant    # AI Logic
├── main.py             # Application Entry Point
└── .env                # Configuration (GitIgnored)
```

---

## Environment Configuration

The application requires specific environment variables for operation. A template is provided in the repository.

**Required Categories**:
- **Application Settings**: `APP_NAME`, `DEBUG`, `SECRET_KEY`
- **Database**: `MONGODB_URL`, `MONGODB_DB_NAME`
- **Security**: `ACCESS_TOKEN_EXPIRE_MINUTES`, `ALGORITHM`
- **AI Services**: `AI_PROVIDER`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`

---

## Development Workflow

1.  **Strict Typing**: All code must utilize Python type hints.
2.  **Linting**: Adherence to PEP 8 standards.
3.  **Modular Development**: New features must be encapsulated within their own module directories.
4.  **Dependency Injection**: Services and repositories must be injected to ensure testability.

---

## Testing & Deployment Responsibility Note

- **Testing**: While the architecture supports comprehensive testing, specific unit test suites are maintained separately.
- **Deployment**: DevOps configurations (Docker, CI/CD pipelines) are managed exclusively by the CYNERZA infrastructure team. This repository focuses solely on application logic.

---

## Contribution Guidelines

This is a proprietary project owned by **CYNERZA Organization**. Contribution is restricted to authorized personnel.
- All code changes must pass review by the lead architect.
- Commits must follow the conventional commit message format.
- No direct pushes to the main branch are permitted.

---

## Author & Organization Credits

**Main Author**: LUCIFER  
**Organization**: CYNERZA

All intellectual property rights and design implementations belong to the CYNERZA Organization.

---

## License & Usage Notice

Copyright © 2024 CYNERZA Organization. All Rights Reserved.

Unauthorized copying, distribution, modification, or use of this source code, via any medium, is strictly prohibited. This software is proprietary and confidential.
