FROM eclipse-temurin:17-jdk-alpine

# The single-file source launcher (Java 11+) compiles and runs a .java file in
# one step with no class-name/filename constraint. -Xint disables JIT to improve
# startup time; -XX:-UsePerfData skips perf data files for ephemeral containers.
LABEL lang.exec="java -Xint -XX:-UsePerfData"

RUN addgroup -S executor && adduser -S executor -G executor

USER executor

ENTRYPOINT ["sh", "-c", "while true; do sleep 3600; done"]
