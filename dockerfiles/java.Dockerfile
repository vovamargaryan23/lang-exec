FROM openjdk:17-slim

CMD ["java", "-v"]

ENTRYPOINT [ "javac" ]