package com.example.crossserver.workerapi;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;

import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

@RestController
@RequestMapping("/api/airflow")
public class AirflowScheduleController {

    private static final String TRUE_VALUE = "true";
    private static final String FALSE_VALUE = "false";

    private final AirflowProperties properties;
    private final RestTemplate restTemplate;

    public AirflowScheduleController(AirflowProperties properties, RestTemplateBuilder restTemplateBuilder) {
        this.properties = properties;
        this.restTemplate = restTemplateBuilder
                .basicAuthentication(properties.getUsername(), properties.getPassword())
                .build();
    }

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "UP");
    }

    @GetMapping("/schedule-mode")
    public ScheduleModeResponse getScheduleMode() {
        return scheduleModeResponse(readFastMode());
    }

    @PostMapping("/schedule-mode")
    public ScheduleModeResponse setScheduleMode(@RequestBody(required = false) ScheduleModeRequest request) {
        boolean fastMode = request != null && Boolean.TRUE.equals(request.fastMode());
        upsertAirflowVariable(fastMode);
        return scheduleModeResponse(fastMode);
    }

    private boolean readFastMode() {
        try {
            ResponseEntity<Map> response = restTemplate.getForEntity(variableUrl(), Map.class);
            Object value = response.getBody() == null ? null : response.getBody().get("value");
            return TRUE_VALUE.equalsIgnoreCase(String.valueOf(value));
        } catch (HttpClientErrorException.NotFound ignored) {
            return false;
        }
    }

    private void upsertAirflowVariable(boolean fastMode) {
        String value = fastMode ? TRUE_VALUE : FALSE_VALUE;
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("key", properties.getScheduleModeVariableKey());
        body.put("value", value);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);

        try {
            restTemplate.getForEntity(variableUrl(), Map.class);
            restTemplate.delete(variableUrl());
        } catch (HttpClientErrorException.NotFound ignored) {
            // Missing variable means this is the first schedule-mode update.
        }

        restTemplate.exchange(variablesUrl(), HttpMethod.POST, entity, String.class);
    }

    private ScheduleModeResponse scheduleModeResponse(boolean fastMode) {
        return new ScheduleModeResponse(
                fastMode,
                fastMode ? "PT1M" : "PT1H",
                properties.getScheduleModeVariableKey()
        );
    }

    private String variablesUrl() {
        return properties.getBaseUrl().replaceAll("/+$", "") + "/api/v1/variables";
    }

    private String variableUrl() {
        String encodedKey = URLEncoder.encode(properties.getScheduleModeVariableKey(), StandardCharsets.UTF_8);
        return variablesUrl() + "/" + encodedKey;
    }

    public record ScheduleModeRequest(Boolean fastMode) {
    }

    public record ScheduleModeResponse(boolean fastMode, String cadence, String variableKey) {
    }
}
