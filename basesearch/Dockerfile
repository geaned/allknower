FROM openjdk:17-jdk-slim as build

WORKDIR /app

COPY build.gradle.kts settings.gradle.kts gradlew ./
COPY gradle ./gradle

RUN ./gradlew build --no-daemon

COPY src ./src

RUN ./gradlew installDist --no-daemon


FROM openjdk:17-jdk-slim

WORKDIR /app

COPY --from=build /app/build/install/basesearch /app

CMD ["./bin/basesearch"]
