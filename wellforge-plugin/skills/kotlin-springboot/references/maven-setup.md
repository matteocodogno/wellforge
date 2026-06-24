# Maven Setup Reference

Complete POM skeleton for a WellForge Spring Boot Kotlin service.

---

## Parent & Properties

```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.4.x</version>
</parent>

<properties>
    <java.version>21</java.version>
    <kotlin.version>2.1.0</kotlin.version>
    <jooq.version>3.19.18</jooq.version>
    <liquibase.version>4.29.2</liquibase.version>
</properties>
```

---

## Core Dependencies

```xml
<dependencies>
    <!-- Web -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- jOOQ — never spring-boot-starter-data-jpa -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-jooq</artifactId>
    </dependency>

    <!-- Liquibase runtime migrations -->
    <dependency>
        <groupId>org.liquibase</groupId>
        <artifactId>liquibase-core</artifactId>
    </dependency>

    <!-- Postgres driver (runtime) -->
    <dependency>
        <groupId>org.postgresql</groupId>
        <artifactId>postgresql</artifactId>
        <scope>runtime</scope>
    </dependency>

    <!-- H2 — only for jOOQ codegen at build time, NOT runtime -->
    <dependency>
        <groupId>com.h2database</groupId>
        <artifactId>h2</artifactId>
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

    <!-- Kotlin logging -->
    <dependency>
        <groupId>io.github.oshai</groupId>
        <artifactId>kotlin-logging-jvm</artifactId>
        <version>7.0.3</version>
    </dependency>

    <!-- Kotlin stdlib -->
    <dependency>
        <groupId>org.jetbrains.kotlin</groupId>
        <artifactId>kotlin-stdlib</artifactId>
    </dependency>

    <!-- Validation -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-validation</artifactId>
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
        <version>1.13.x</version>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>io.kotest</groupId>
        <artifactId>kotest-assertions-core-jvm</artifactId>
        <version>5.9.x</version>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>org.testcontainers</groupId>
        <artifactId>postgresql</artifactId>
        <scope>test</scope>
    </dependency>
</dependencies>
```

---

## Dependency Management (BOM)

```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.modulith</groupId>
            <artifactId>spring-modulith-bom</artifactId>
            <version>1.3.x</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
        <dependency>
            <groupId>org.testcontainers</groupId>
            <artifactId>testcontainers-bom</artifactId>
            <version>1.20.x</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

---

## Build Plugins

### kotlin-maven-plugin

```xml
<plugin>
    <groupId>org.jetbrains.kotlin</groupId>
    <artifactId>kotlin-maven-plugin</artifactId>
    <version>${kotlin.version}</version>
    <configuration>
        <args>
            <arg>-Xjsr305=strict</arg>
        </args>
        <compilerPlugins>
            <plugin>spring</plugin>
            <!-- NO kotlin-jpa plugin — we use jOOQ, not JPA -->
        </compilerPlugins>
    </configuration>
    <dependencies>
        <dependency>
            <groupId>org.jetbrains.kotlin</groupId>
            <artifactId>kotlin-maven-allopen</artifactId>
            <version>${kotlin.version}</version>
        </dependency>
    </dependencies>
    <executions>
        <execution>
            <id>compile</id>
            <goals><goal>compile</goal></goals>
            <configuration>
                <sourceDirs>
                    <sourceDir>${project.basedir}/src/main/kotlin</sourceDir>
                    <!-- Include jOOQ generated sources -->
                    <sourceDir>${project.build.directory}/generated-sources/jooq</sourceDir>
                </sourceDirs>
            </configuration>
        </execution>
        <execution>
            <id>test-compile</id>
            <goals><goal>test-compile</goal></goals>
        </execution>
    </executions>
</plugin>
```

### jooq-codegen-maven plugin

This plugin generates Kotlin jOOQ records from Liquibase migrations using H2 in-memory.  
It runs in the `generate-sources` phase, before compilation.

```xml
<plugin>
    <groupId>org.jooq</groupId>
    <artifactId>jooq-codegen-maven</artifactId>
    <version>${jooq.version}</version>
    <executions>
        <execution>
            <goals>
                <goal>generate</goal>
            </goals>
        </execution>
    </executions>
    <dependencies>
        <!-- jOOQ Liquibase extension for codegen -->
        <dependency>
            <groupId>org.jooq</groupId>
            <artifactId>jooq-meta-extensions-liquibase</artifactId>
            <version>${jooq.version}</version>
        </dependency>
        <!-- H2 used only during codegen -->
        <dependency>
            <groupId>com.h2database</groupId>
            <artifactId>h2</artifactId>
            <version>${h2.version}</version>
        </dependency>
        <!-- Liquibase needed by the extension -->
        <dependency>
            <groupId>org.liquibase</groupId>
            <artifactId>liquibase-core</artifactId>
            <version>${liquibase.version}</version>
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
                        <value>${basedir}/src/main/resources/db/changelog</value>
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
                    <!-- Exclude test-only and postgres-only changesets during codegen -->
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
                <!-- Adjust packageName to match your service -->
                <packageName>com.example.yourservice.dal.jooq</packageName>
                <directory>target/generated-sources/jooq</directory>
            </target>
            <strategy>
                <name>org.jooq.codegen.DefaultGeneratorStrategy</name>
            </strategy>
        </generator>
    </configuration>
</plugin>
```

### spring-boot-maven-plugin

```xml
<plugin>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-maven-plugin</artifactId>
</plugin>
```

---

## Build order note

The codegen plugin runs in `generate-sources` (before `compile`).  
The Kotlin compiler includes `target/generated-sources/jooq` as a source directory.  
This means **you must run `mvn generate-sources` (or any later phase) before your IDE resolves jOOQ types**.  
Add a `.mvn/wrapper/` to pin the Maven version and ensure reproducible builds.
