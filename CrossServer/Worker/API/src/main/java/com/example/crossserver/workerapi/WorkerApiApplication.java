package com.example.crossserver.workerapi;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

@SpringBootApplication
@EnableConfigurationProperties(AirflowProperties.class)
public class WorkerApiApplication {

    public static void main(String[] args) {
        SpringApplication.run(WorkerApiApplication.class, args);
    }
}
