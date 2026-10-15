{{/*
Expand the name of the chart.
*/}}
{{- define "saas-renewal-watchtower.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Fully qualified app name.
*/}}
{{- define "saas-renewal-watchtower.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "saas-renewal-watchtower.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "saas-renewal-watchtower.labels" -}}
helm.sh/chart: {{ include "saas-renewal-watchtower.chart" . }}
{{ include "saas-renewal-watchtower.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "saas-renewal-watchtower.selectorLabels" -}}
app.kubernetes.io/name: {{ include "saas-renewal-watchtower.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service account name.
*/}}
{{- define "saas-renewal-watchtower.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "saas-renewal-watchtower.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Immutable image reference rendered from repository and digest.
*/}}
{{- define "saas-renewal-watchtower.image" -}}
{{- printf "%s@%s" .Values.image.repository .Values.image.digest }}
{{- end }}
