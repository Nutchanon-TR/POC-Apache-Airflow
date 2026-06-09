package com.example.crossserver.workerbatch;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

@SpringBootApplication
@EnableConfigurationProperties(ReverseBatchProperties.class)
public class WorkerBatchApplication {

    public static void main(String[] args) {
        SpringApplication.run(WorkerBatchApplication.class, args);
    }
}
