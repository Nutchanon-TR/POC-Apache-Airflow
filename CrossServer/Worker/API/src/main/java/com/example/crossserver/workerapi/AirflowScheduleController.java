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

    // ── health ───────────────────────────────────────────────────────────────

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "UP");
    }

    // ── trigger DAG immediately ───────────────────────────────────────────────

    @PostMapping("/trigger")
    public TriggerResponse triggerDag(@RequestBody(required = false) TriggerRequest request) {
        String dagId = (request != null && request.dagId() != null)
                ? request.dagId()
                : properties.getDefaultDagId();

        Map<String, Object> conf = (request != null) ? request.conf() : null;

        String url = dagRunsUrl(dagId);
        Map<String, Object> body = new LinkedHashMap<>();
        if (conf != null && !conf.isEmpty()) {
            body.put("conf", conf);
        }

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);

        ResponseEntity<Map> response = restTemplate.exchange(url, HttpMethod.POST, entity, Map.class);
        String dagRunId = response.getBody() == null ? null : (String) response.getBody().get("dag_run_id");
        return new TriggerResponse(dagRunId, dagId);
    }

    // ── schedule-mode (existing) ──────────────────────────────────────────────

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

    // ── internals ────────────────────────────────────────────────────────────

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
            // first call — variable does not exist yet
        }

        restTemplate.exchange(variablesUrl(), HttpMethod.POST, entity, String.class);
    }

    private ScheduleModeResponse scheduleModeResponse(boolean fastMode) {
        return new ScheduleModeResponse(
                fastMode,
                fastMode ? "PT1M" : "PT1H",
                properties.getScheduleModeVariableKey());
    }

    private String baseUrl() {
        return properties.getBaseUrl().replaceAll("/+$", "");
    }

    private String dagRunsUrl(String dagId) {
        return baseUrl() + "/api/v1/dags/" + dagId + "/dagRuns";
    }

    private String variablesUrl() {
        return baseUrl() + "/api/v1/variables";
    }

    private String variableUrl() {
        String encodedKey = URLEncoder.encode(properties.getScheduleModeVariableKey(), StandardCharsets.UTF_8);
        return variablesUrl() + "/" + encodedKey;
    }

    // ── records ───────────────────────────────────────────────────────────────

    public record TriggerRequest(String dagId, Map<String, Object> conf) {
    }

    public record TriggerResponse(String dagRunId, String dagId) {
    }

    public record ScheduleModeRequest(Boolean fastMode) {
    }

    public record ScheduleModeResponse(boolean fastMode, String cadence, String variableKey) {
    }
}
