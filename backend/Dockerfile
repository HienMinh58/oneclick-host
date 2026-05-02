# ─────────────────────────────────────
# Stage 1: Build
# ─────────────────────────────────────
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src

# Copy solution and project files first (layer caching)
COPY OneClickHost.Api/*.csproj OneClickHost.Api/
RUN dotnet restore OneClickHost.Api/OneClickHost.Api.csproj

# Copy everything and build
COPY . .
WORKDIR /src/OneClickHost.Api
RUN dotnet publish -c Release -o /app/publish

# ─────────────────────────────────────
# Stage 2: Runtime
# ─────────────────────────────────────
FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime
WORKDIR /app

COPY --from=build /app/publish .

ENV ASPNETCORE_URLS=http://+:5000
EXPOSE 5000

ENTRYPOINT ["dotnet", "OneClickHost.Api.dll"]
