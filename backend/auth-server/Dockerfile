# ---- build ----
FROM eclipse-temurin:17-jdk AS build
WORKDIR /src
COPY . .
RUN chmod +x gradlew && ./gradlew :app:installDist --no-daemon -q

# ---- run ----
FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=build /src/app/build/install/app /app
EXPOSE 8080
CMD ["/app/bin/app"]
