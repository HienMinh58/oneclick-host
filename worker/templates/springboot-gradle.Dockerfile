# ─────────────────────────────────────
# Spring Boot (Gradle) Dockerfile Template
# ─────────────────────────────────────
FROM gradle:8.5-jdk21-alpine AS build
WORKDIR /app

# Copy build files first (layer caching)
COPY build.gradle* settings.gradle* ./
COPY gradle ./gradle
RUN gradle dependencies --no-daemon || true

# Copy source and build
COPY src ./src
RUN gradle bootJar --no-daemon -x test

# Runtime
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY --from=build /app/build/libs/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
