package com.example.crossserver.workerapi;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "airflow")
public class AirflowProperties {

    private String baseUrl = "http://airflow-webserver:8080";
    private String scheduleModeVariableKey = "batch_fast_mode";
    private String username = "admin";
    private String password = "admin";

    public String getBaseUrl() {
        return baseUrl;
    }

    public void setBaseUrl(String baseUrl) {
        this.baseUrl = baseUrl;
    }

    public String getScheduleModeVariableKey() {
        return scheduleModeVariableKey;
    }

    public void setScheduleModeVariableKey(String scheduleModeVariableKey) {
        this.scheduleModeVariableKey = scheduleModeVariableKey;
    }

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public String getPassword() {
        return password;
    }

    public void setPassword(String password) {
        this.password = password;
    }
}
