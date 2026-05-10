{{/*
Expand the name of the chart.
*/}}
{{- define "webbuchhaltung.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels applied to all resources.
*/}}
{{- define "webbuchhaltung.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/name: {{ include "webbuchhaltung.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels used by Deployments and Services to match pods.
*/}}
{{- define "webbuchhaltung.selectorLabels" -}}
app.kubernetes.io/name: {{ include "webbuchhaltung.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
