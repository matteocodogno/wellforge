#!/usr/bin/env bash
# Usage: scaffold.sh <artifactId> <serviceName> <ServiceName> <basePackage>
# Example: scaffold.sh order-service order Order ch.welld.soa.order
set -euo pipefail

ARTIFACT_ID="$1"
SERVICE_NAME="$2"
SERVICE_NAME_CAP="$3"
BASE_PACKAGE="$4"
PACKAGE_PATH="${BASE_PACKAGE//.//}"
JOOQ_PACKAGE="${BASE_PACKAGE}.dal.jooq"

ROOT="./${ARTIFACT_ID}"

echo "Scaffolding ${ARTIFACT_ID} → ${BASE_PACKAGE}"

# ─── Directory tree ───────────────────────────────────────────────────────────
mkdir -p "${ROOT}/src/main/kotlin/${PACKAGE_PATH}/common/model"
mkdir -p "${ROOT}/src/main/kotlin/${PACKAGE_PATH}/common/web"
mkdir -p "${ROOT}/src/main/kotlin/${PACKAGE_PATH}/common/config"
mkdir -p "${ROOT}/src/main/java/${PACKAGE_PATH}/common"
mkdir -p "${ROOT}/src/main/resources/db/changelog/changes"
mkdir -p "${ROOT}/src/test/kotlin/${PACKAGE_PATH}"
mkdir -p "${ROOT}/src/test/resources"

# ─── pom.xml ─────────────────────────────────────────────────────────────────
# NOTE: Uses Spring Boot 4.0.0.
# KEY SB4 CHANGE: spring-boot-starter-web → spring-boot-starter-webmvc
# jOOQ version pinned explicitly (BOM property name changed in SB4)
cat > "${ROOT}/pom.xml" << POMEOF
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>4.0.0</version>
        <relativePath/>
    </parent>

    <groupId>ch.welld.soa</groupId>
    <artifactId>${ARTIFACT_ID}</artifactId>
    <version>0.0.1-SNAPSHOT</version>
    <name>${ARTIFACT_ID}</name>

    <properties>
        <java.version>21</java.version>
        <kotlin.version>2.1.20</kotlin.version>
        <jooq.version>3.19.18</jooq.version>
        <liquibase.version>4.29.2</liquibase.version>
        <kotlin-logging.version>7.0.3</kotlin-logging.version>
        <mockk.version>1.13.14</mockk.version>
        <kotest.version>5.9.1</kotest.version>
        <spring-modulith.version>2.0.0</spring-modulith.version>
        <testcontainers.version>1.20.4</testcontainers.version>
        <h2.version>2.3.232</h2.version>
    </properties>

    <dependencyManagement>
        <dependencies>
            <dependency>
                <groupId>org.springframework.modulith</groupId>
                <artifactId>spring-modulith-bom</artifactId>
                <version>\${spring-modulith.version}</version>
                <type>pom</type>
                <scope>import</scope>
            </dependency>
            <dependency>
                <groupId>org.testcontainers</groupId>
                <artifactId>testcontainers-bom</artifactId>
                <version>\${testcontainers.version}</version>
                <type>pom</type>
                <scope>import</scope>
            </dependency>
        </dependencies>
    </dependencyManagement>

    <dependencies>
        <!-- Web — NOTE: spring-boot-starter-web was renamed in SB4 -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-webmvc</artifactId>
        </dependency>

        <!-- jOOQ -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-jooq</artifactId>
        </dependency>

        <!-- Liquibase — use the Spring Boot starter, not liquibase-core directly -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-liquibase</artifactId>
        </dependency>

        <!-- Postgres (runtime) -->
        <dependency>
            <groupId>org.postgresql</groupId>
            <artifactId>postgresql</artifactId>
            <scope>runtime</scope>
        </dependency>

        <!-- H2 (codegen only — never runtime) -->
        <dependency>
            <groupId>com.h2database</groupId>
            <artifactId>h2</artifactId>
            <version>\${h2.version}</version>
            <scope>provided</scope>
        </dependency>

        <!-- Docker Compose dev support -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-docker-compose</artifactId>
            <optional>true</optional>
        </dependency>

        <!-- Spring Modulith -->
        <dependency>
            <groupId>org.springframework.modulith</groupId>
            <artifactId>spring-modulith-starter-core</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.modulith</groupId>
            <artifactId>spring-modulith-starter-jooq</artifactId>
        </dependency>

        <!-- Validation -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>

        <!-- Kotlin -->
        <dependency>
            <groupId>org.jetbrains.kotlin</groupId>
            <artifactId>kotlin-stdlib</artifactId>
        </dependency>
        <dependency>
            <groupId>org.jetbrains.kotlin</groupId>
            <artifactId>kotlin-reflect</artifactId>
        </dependency>

        <!-- kotlin-logging -->
        <dependency>
            <groupId>io.github.oshai</groupId>
            <artifactId>kotlin-logging-jvm</artifactId>
            <version>\${kotlin-logging.version}</version>
        </dependency>

        <!-- Test -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework.modulith</groupId>
            <artifactId>spring-modulith-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>io.mockk</groupId>
            <artifactId>mockk</artifactId>
            <version>\${mockk.version}</version>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>io.kotest</groupId>
            <artifactId>kotest-assertions-core-jvm</artifactId>
            <version>\${kotest.version}</version>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.testcontainers</groupId>
            <artifactId>postgresql</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.testcontainers</groupId>
            <artifactId>junit-jupiter</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <sourceDirectory>\${project.basedir}/src/main/kotlin</sourceDirectory>
        <testSourceDirectory>\${project.basedir}/src/test/kotlin</testSourceDirectory>
        <plugins>
            <!-- kotlin-maven-plugin — version must match kotlin.version property -->
            <plugin>
                <groupId>org.jetbrains.kotlin</groupId>
                <artifactId>kotlin-maven-plugin</artifactId>
                <version>\${kotlin.version}</version>
                <configuration>
                    <args>
                        <arg>-Xjsr305=strict</arg>
                    </args>
                    <compilerPlugins>
                        <plugin>spring</plugin>
                    </compilerPlugins>
                </configuration>
                <dependencies>
                    <dependency>
                        <groupId>org.jetbrains.kotlin</groupId>
                        <artifactId>kotlin-maven-allopen</artifactId>
                        <version>\${kotlin.version}</version>
                    </dependency>
                </dependencies>
                <executions>
                    <execution>
                        <id>compile</id>
                        <goals><goal>compile</goal></goals>
                        <configuration>
                            <sourceDirs>
                                <sourceDir>\${project.basedir}/src/main/kotlin</sourceDir>
                                <sourceDir>\${project.basedir}/src/main/java</sourceDir>
                                <sourceDir>\${project.build.directory}/generated-sources/jooq</sourceDir>
                            </sourceDirs>
                        </configuration>
                    </execution>
                    <execution>
                        <id>test-compile</id>
                        <goals><goal>test-compile</goal></goals>
                    </execution>
                </executions>
            </plugin>

            <!-- jOOQ codegen from Liquibase via H2 — version pinned explicitly -->
            <plugin>
                <groupId>org.jooq</groupId>
                <artifactId>jooq-codegen-maven</artifactId>
                <version>\${jooq.version}</version>
                <executions>
                    <execution>
                        <goals><goal>generate</goal></goals>
                    </execution>
                </executions>
                <dependencies>
                    <dependency>
                        <groupId>org.jooq</groupId>
                        <artifactId>jooq-meta-extensions-liquibase</artifactId>
                        <version>\${jooq.version}</version>
                    </dependency>
                    <dependency>
                        <groupId>com.h2database</groupId>
                        <artifactId>h2</artifactId>
                        <version>\${h2.version}</version>
                    </dependency>
                    <dependency>
                        <groupId>org.liquibase</groupId>
                        <artifactId>liquibase-core</artifactId>
                        <version>\${liquibase.version}</version>
                    </dependency>
                </dependencies>
                <configuration>
                    <detail>true</detail>
                    <generator>
                        <name>org.jooq.codegen.KotlinGenerator</name>
                        <database>
                            <name>org.jooq.meta.extensions.liquibase.LiquibaseDatabase</name>
                            <properties>
                                <property>
                                    <key>rootPath</key>
                                    <value>\${basedir}/src/main/resources/db/changelog</value>
                                </property>
                                <property>
                                    <key>scripts</key>
                                    <value>db.changelog-master.yaml</value>
                                </property>
                                <property>
                                    <key>includeLiquibaseTables</key>
                                    <value>false</value>
                                </property>
                                <property>
                                    <key>database.liquibaseSchemaName</key>
                                    <value>public</value>
                                </property>
                                <property>
                                    <key>changeLogParameters.contexts</key>
                                    <value>!test,!generate_skip</value>
                                </property>
                            </properties>
                        </database>
                        <generate>
                            <deprecated>false</deprecated>
                            <records>true</records>
                            <pojos>false</pojos>
                        </generate>
                        <target>
                            <packageName>${JOOQ_PACKAGE}</packageName>
                            <directory>target/generated-sources/jooq</directory>
                        </target>
                        <strategy>
                            <name>org.jooq.codegen.DefaultGeneratorStrategy</name>
                        </strategy>
                    </generator>
                </configuration>
            </plugin>

            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
POMEOF

# ─── Application.kt ───────────────────────────────────────────────────────────
cat > "${ROOT}/src/main/kotlin/${PACKAGE_PATH}/Application.kt" << EOF
package ${BASE_PACKAGE}

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

@SpringBootApplication
class ${SERVICE_NAME_CAP}Application

fun main(args: Array<String>) {
    runApplication<${SERVICE_NAME_CAP}Application>(*args)
}
EOF

# ─── Result.kt ────────────────────────────────────────────────────────────────
cat > "${ROOT}/src/main/kotlin/${PACKAGE_PATH}/common/model/Result.kt" << EOF
package ${BASE_PACKAGE}.common.model

import org.springframework.dao.DataAccessException

@Suppress("TooManyFunctions")
sealed class Result<out T> {
    data class Success<T>(val value: T) : Result<T>()
    data class Failure(val error: DomainError) : Result<Nothing>()

    val isSuccess: Boolean get() = this is Success
    val isFailure: Boolean get() = this is Failure

    inline fun <R> map(transform: (T) -> R): Result<R> =
        when (this) {
            is Success -> Success(transform(value))
            is Failure -> this
        }

    inline fun mapError(transform: (DomainError) -> DomainError): Result<T> =
        when (this) {
            is Success -> this
            is Failure -> Failure(transform(error))
        }

    inline fun <R> flatMap(transform: (T) -> Result<R>): Result<R> =
        when (this) {
            is Success -> transform(value)
            is Failure -> this
        }

    inline fun <R> fold(onSuccess: (T) -> R, onFailure: (DomainError) -> R): R =
        when (this) {
            is Success -> onSuccess(value)
            is Failure -> onFailure(error)
        }

    inline fun onSuccess(action: (T) -> Unit): Result<T> {
        if (this is Success) action(value)
        return this
    }

    inline fun onFailure(action: (DomainError) -> Unit): Result<T> {
        if (this is Failure) action(error)
        return this
    }

    fun getOrThrow(): T =
        when (this) {
            is Success -> value
            is Failure -> throw error.toException()
        }

    fun getOrElse(default: @UnsafeVariance T): T =
        when (this) {
            is Success -> value
            is Failure -> default
        }

    inline fun getOrElse(default: (DomainError) -> @UnsafeVariance T): T =
        when (this) {
            is Success -> value
            is Failure -> default(error)
        }

    fun getOrNull(): T? =
        when (this) {
            is Success -> value
            is Failure -> null
        }

    inline fun recover(transform: (DomainError) -> @UnsafeVariance T): Result<T> =
        when (this) {
            is Success -> this
            is Failure -> Success(transform(error))
        }

    inline fun recoverWith(transform: (DomainError) -> Result<@UnsafeVariance T>): Result<T> =
        when (this) {
            is Success -> this
            is Failure -> transform(error)
        }

    companion object {
        fun <T> success(value: T): Result<T> = Success(value)
        fun <T> failure(error: DomainError): Result<T> = Failure(error)

        inline fun <T> catching(block: () -> T): Result<T> =
            try {
                Success(block())
            } catch (e: DataAccessException) {
                Failure(DomainError.DatabaseError(e.message ?: "Unknown database error", e))
            } catch (e: Exception) {
                Failure(DomainError.UnexpectedError(e.message ?: "Unknown error", e))
            }
    }
}
EOF

# ─── DomainError.kt ───────────────────────────────────────────────────────────
cat > "${ROOT}/src/main/kotlin/${PACKAGE_PATH}/common/model/DomainError.kt" << EOF
package ${BASE_PACKAGE}.common.model

sealed class DomainError {
    abstract val message: String
    abstract val cause: Throwable?

    data class DatabaseError(
        override val message: String,
        override val cause: Throwable? = null,
    ) : DomainError()

    data class ValidationError(
        override val message: String,
        override val cause: Throwable? = null,
    ) : DomainError()

    data class NotFoundError(
        override val message: String,
        override val cause: Throwable? = null,
    ) : DomainError()

    data class UnexpectedError(
        override val message: String,
        override val cause: Throwable? = null,
    ) : DomainError()

    data class StateError(
        override val message: String,
        override val cause: Throwable? = null,
    ) : DomainError()

    fun toException(): RuntimeException =
        when (this) {
            is DatabaseError   -> DatabaseException(message, cause)
            is ValidationError -> ValidationException(message, cause)
            is NotFoundError   -> NotFoundException(message, cause)
            is UnexpectedError -> UnexpectedException(message, cause)
            is StateError      -> IllegalStateException(message, cause)
        }
}

class DatabaseException(message: String, cause: Throwable? = null) : RuntimeException(message, cause)
class ValidationException(message: String, cause: Throwable? = null) : RuntimeException(message, cause)
class NotFoundException(message: String, cause: Throwable? = null) : RuntimeException(message, cause)
class UnexpectedException(message: String, cause: Throwable? = null) : RuntimeException(message, cause)
EOF

# ─── GlobalExceptionHandler.kt ────────────────────────────────────────────────
cat > "${ROOT}/src/main/kotlin/${PACKAGE_PATH}/common/web/GlobalExceptionHandler.kt" << EOF
package ${BASE_PACKAGE}.common.web

import ${BASE_PACKAGE}.common.model.DatabaseException
import ${BASE_PACKAGE}.common.model.DomainError
import ${BASE_PACKAGE}.common.model.NotFoundException
import ${BASE_PACKAGE}.common.model.UnexpectedException
import ${BASE_PACKAGE}.common.model.ValidationException
import io.github.oshai.kotlinlogging.KotlinLogging
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.ControllerAdvice
import org.springframework.web.bind.annotation.ExceptionHandler

private val logger = KotlinLogging.logger {}

data class ErrorResponse(val message: String)

fun DomainError.toResponse(): ResponseEntity<ErrorResponse> =
    when (this) {
        is DomainError.NotFoundError   -> ResponseEntity.status(404).body(ErrorResponse(message))
        is DomainError.ValidationError -> ResponseEntity.status(400).body(ErrorResponse(message))
        is DomainError.StateError      -> ResponseEntity.status(409).body(ErrorResponse(message))
        is DomainError.DatabaseError   -> ResponseEntity.status(500).body(ErrorResponse("Internal error"))
        is DomainError.UnexpectedError -> ResponseEntity.status(500).body(ErrorResponse("Internal error"))
    }

@ControllerAdvice
class GlobalExceptionHandler {

    @ExceptionHandler(NotFoundException::class)
    fun handleNotFound(ex: NotFoundException): ResponseEntity<ErrorResponse> =
        ResponseEntity.status(404).body(ErrorResponse(ex.message ?: "Not found"))

    @ExceptionHandler(ValidationException::class)
    fun handleValidation(ex: ValidationException): ResponseEntity<ErrorResponse> =
        ResponseEntity.status(400).body(ErrorResponse(ex.message ?: "Bad request"))

    @ExceptionHandler(DatabaseException::class)
    fun handleDatabase(ex: DatabaseException): ResponseEntity<ErrorResponse> {
        logger.error(ex) { "Database error" }
        return ResponseEntity.status(500).body(ErrorResponse("Internal error"))
    }

    @ExceptionHandler(UnexpectedException::class)
    fun handleUnexpected(ex: UnexpectedException): ResponseEntity<ErrorResponse> {
        logger.error(ex) { "Unexpected error" }
        return ResponseEntity.status(500).body(ErrorResponse("Internal error"))
    }
}
EOF

# ─── package-info.java for common module ──────────────────────────────────────
# Spring Modulith's @ApplicationModule is a Java package annotation.
# Kotlin has no package-level annotation support, so this MUST be a .java file
# even in a pure Kotlin project. This is not a mistake.
mkdir -p "${ROOT}/src/main/java/${PACKAGE_PATH}/common"
cat > "${ROOT}/src/main/java/${PACKAGE_PATH}/common/package-info.java" << EOF
@ApplicationModule(type = ApplicationModule.Type.OPEN)
package ${BASE_PACKAGE}.common;

import org.springframework.modulith.ApplicationModule;
EOF

# ─── CommonConfiguration.kt ───────────────────────────────────────────────────
# No @ApplicationModule here — that annotation lives in package-info.java above.
cat > "${ROOT}/src/main/kotlin/${PACKAGE_PATH}/common/config/CommonConfiguration.kt" << EOF
package ${BASE_PACKAGE}.common.config

import org.springframework.context.annotation.Configuration

@Configuration
class CommonConfiguration
EOF

# ─── application.yml ──────────────────────────────────────────────────────────
cat > "${ROOT}/src/main/resources/application.yml" << EOF
spring:
  application:
    name: ${ARTIFACT_ID}
  liquibase:
    change-log: classpath:/db/changelog/db.changelog-master.yaml
    enabled: true
  jooq:
    sql-dialect: POSTGRES

logging:
  level:
    ${BASE_PACKAGE}: DEBUG
    org.jooq.tools.LoggerListener: DEBUG
EOF

# ─── application-test.yml ─────────────────────────────────────────────────────
cat > "${ROOT}/src/test/resources/application-test.yml" << EOF
spring:
  liquibase:
    enabled: true
  docker:
    compose:
      enabled: false
EOF

# ─── compose.yaml ─────────────────────────────────────────────────────────────
cat > "${ROOT}/compose.yaml" << EOF
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: ${SERVICE_NAME}
      POSTGRES_USER: ${SERVICE_NAME}
      POSTGRES_PASSWORD: secret
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${SERVICE_NAME}"]
      interval: 5s
      timeout: 5s
      retries: 5
EOF

# ─── Liquibase master changelog ───────────────────────────────────────────────
cat > "${ROOT}/src/main/resources/db/changelog/db.changelog-master.yaml" << EOF
databaseChangeLog:
  - includeAll:
      path: changes/
      relativeToChangelogFile: true
EOF

# ─── Placeholder migrations (H2 + Postgres dual-DBMS pattern) ────────────────
cat > "${ROOT}/src/main/resources/db/changelog/changes/001-init-postgres.sql" << EOF
--liquibase formatted sql
-- Add your first Postgres migration here.
-- Example:
--
-- --changeset ${SERVICE_NAME}:001-create-example dbms:postgresql
-- CREATE TABLE example (
--     id BIGSERIAL PRIMARY KEY,
--     name TEXT NOT NULL,
--     created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
-- );
-- --rollback DROP TABLE example;
EOF

cat > "${ROOT}/src/main/resources/db/changelog/changes/001-init-h2.sql" << EOF
--liquibase formatted sql
-- H2-compatible mirror of 001-init-postgres.sql for jOOQ codegen.
-- Example:
--
-- --changeset ${SERVICE_NAME}:001-create-example dbms:h2
-- CREATE TABLE example (
--     id BIGINT AUTO_INCREMENT PRIMARY KEY,
--     name VARCHAR(255) NOT NULL,
--     created_at TIMESTAMP NOT NULL DEFAULT NOW()
-- );
-- --rollback DROP TABLE example;
EOF

# ─── Modularity test ──────────────────────────────────────────────────────────
cat > "${ROOT}/src/test/kotlin/${PACKAGE_PATH}/ModularityTest.kt" << EOF
package ${BASE_PACKAGE}

import org.junit.jupiter.api.Test
import org.springframework.modulith.core.ApplicationModules
import org.springframework.modulith.docs.Documenter

class ModularityTest {

    private val modules = ApplicationModules.of(${SERVICE_NAME_CAP}Application::class.java)

    @Test
    fun \`modules should not have illegal dependencies\`() {
        modules.verify()
    }

    @Test
    fun \`should write module documentation\`() {
        Documenter(modules).writeDocumentation()
    }
}
EOF

# ─── .gitignore ───────────────────────────────────────────────────────────────
cat > "${ROOT}/.gitignore" << EOF
target/
*.class
*.jar
*.war
*.ear
.idea/
*.iml
.DS_Store
*.log
# mise local overrides — never commit
.mise.local.toml
.mise.*.local.toml
EOF

# ─── mise.toml ────────────────────────────────────────────────────────────────
cat > "${ROOT}/mise.toml" << EOF
# ${ARTIFACT_ID}/mise.toml
# Tools (java, maven, node, pnpm) are declared in the root mise.toml.
# This file adds service-specific tasks only.
# Run \`mise trust\` once after cloning.

[tasks.install]
description = "Resolve Maven dependencies"
run         = "./mvnw dependency:resolve -q"
sources     = ["pom.xml"]

[tasks.build]
description = "Compile the backend"
depends     = ["install"]
run         = "./mvnw clean compile -q --no-transfer-progress"
sources     = ["pom.xml", "src/**/*.kt"]
outputs     = ["target/classes/**/*"]

[tasks.test]
description = "Run backend tests"
depends     = ["build"]
run         = "./mvnw test -q --no-transfer-progress"
sources     = ["src/**/*.kt"]

[tasks.run]
description = "Start the Spring Boot service"
run         = "./mvnw spring-boot:run"

[tasks.lint]
description = "ktlint check"
run         = "./mvnw ktlintCheck -q"
sources     = ["src/**/*.kt"]

[tasks."lint:fix"]
description = "ktlint format"
run         = "./mvnw ktlintFormat -q"
sources     = ["src/**/*.kt"]

[tasks.generate]
description = "Generate jOOQ sources from Liquibase changelogs"
run         = "./mvnw generate-sources -q --no-transfer-progress"
sources     = ["src/main/resources/db/changelog/**/*.sql"]
outputs     = ["target/generated-sources/jooq/**/*"]
EOF

# ─── Maven Wrapper ────────────────────────────────────────────────────────────
echo "Generating Maven wrapper..."
cd "${ROOT}"
if command -v mise &>/dev/null && mise ls --current 2>/dev/null | grep -q "maven"; then
    mise exec -- mvn wrapper:wrapper -N -q 2>&1
    echo "✓ Maven wrapper generated via mise-managed mvn"
elif command -v mvn &>/dev/null; then
    mvn wrapper:wrapper -N -q 2>&1
    echo "✓ Maven wrapper generated via system mvn"
else
    echo "⚠ Maven not found — install: mise plugin install maven https://github.com/mise-plugins/mise-maven && mise install"
    echo "  Then: mise exec -- mvn wrapper:wrapper -N"
fi
cd - > /dev/null

# ─── Zip the project ──────────────────────────────────────────────────────────
cd "$(dirname "${ROOT}")"
zip -r "${ARTIFACT_ID}.zip" "${ARTIFACT_ID}/" > /dev/null
cp "${ARTIFACT_ID}.zip" /mnt/user-data/outputs/
echo "Done → /mnt/user-data/outputs/${ARTIFACT_ID}.zip"

