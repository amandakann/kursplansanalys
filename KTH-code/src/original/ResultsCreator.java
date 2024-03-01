package KTHoriginal;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;


/**
 * A class for creating the results for my thesis
 * "Analyzing KTH's course syllabuses from a pedagogical perspective".
 * The needed input CSV file is constructed using GetSyllabus.java.
 * 
 * @author Joakim Lindberg
 * @version 2017-06-01
 */
public class ResultsCreator {
        // Should cycle 3 courses be included in the output?
        final private boolean outputCycle3 = false;
	
	// Contains a line from the input file.
	private List<String> line;
	
	// Used for checking if each variable is fulfilled. 
	private int[] var;
	
	// Used for constructing the output CSV file.
	private StringBuilder sbOutputCSV = new StringBuilder();
	
	
	/**
	 * Creates the wanted results using the given input CSV file. 
	 * 
	 * @param inputFileName Path to the file containing the input CSV data from GetSyllabus.
	 * @throws IOException
	 */
	public ResultsCreator(String inputFileName, String outputFileName) throws IOException {
		
		// Contains all the lines (outer list) and their content column by column (inner list).
		List<List<String>> lines = new ArrayList<>();
		
		// Read the output CSV file constructed by GetSyllabus.java.
		Files.lines(Paths.get(inputFileName)).forEach(line -> {
			String[] tokens = line.split(";");
			lines.add(Arrays.asList(tokens));
		});
		
		// Get the indexes of the relevant columns in the output CSV file.
		int iCode = lines.get(0).indexOf("code");
		int iSyllLangSv = lines.get(0).indexOf("syll_lang_swe");
		int iSyllLangEn = lines.get(0).indexOf("syll_lang_eng");
		int iContent = lines.get(0).indexOf("content");
		int iGoalsSv = lines.get(0).indexOf("goals_swe");
		int iLiterature = lines.get(0).indexOf("literature");
		int iExamComments = lines.get(0).indexOf("exam_comments");
		int iReqForGrade = lines.get(0).indexOf("req_for_grade");
		int iValidFrom = lines.get(0).indexOf("valid_from");
		int iInstructionLang = lines.get(0).indexOf("instruction_lang");
		int iCycle = lines.get(0).indexOf("cycle");
		int iCredits = lines.get(0).indexOf("credits");
		int iTitleSv = lines.get(0).indexOf("title_swe");
		int iTitleEn = lines.get(0).indexOf("title_eng");
		int iGradeScale = lines.get(0).indexOf("grade_scale");
		int iDepartment = lines.get(0).indexOf("department");
		int iNExamModules = lines.get(0).indexOf("n_exam_modules");
		int iEthics = lines.get(0).indexOf("ethics_keywords");
		int iNILOs = lines.get(0).indexOf("n_ilos");
		
		// Get the indexes of the Bloom's taxonomy columns in the output CSV file.
		String[] bloomColumnNames = {"bloom_knowledge", "bloom_comprehension", "bloom_application",
				"bloom_analysis", "bloom_evaluation", "bloom_synthesis"};
		int[] bloomIndexes = new int[6];
		for (int i = 0; i < bloomColumnNames.length; i++) {
			bloomIndexes[i] = lines.get(0).indexOf(bloomColumnNames[i]);
		}
		
		// Output the header line.
		sbOutputCSV.append("course_code;cycle;n_credits;school;laws;kth_regulations;"
				+ "kth_recommendations;suhf;esg;research;avg_blooms;total\n");
		
		// Process each course (skip the first line since it is the header).
		for (int i = 1; i < lines.size(); i++) {
			line = lines.get(i);
			var = new int[lines.get(0).size()];
			
			if (!outputCycle3 && Integer.parseInt(line.get(iCycle)) == 3) continue;
			
			// Set variables if the value is above zero.
			setVarIfAboveZero(iGoalsSv);
			setVarIfAboveZero(iTitleSv);
			setVarIfAboveZero(iTitleEn);
			setVarIfAboveZero(iValidFrom);
			var[iValidFrom] = 1; // ValidFrom is always stated in KTH course syllabuses
			setVarIfAboveZero(iContent);
			setVarIfAboveZero(iLiterature);
			setVarIfAboveZero(iReqForGrade);
			setVarIfAboveZero(iExamComments);
			setVarIfAboveZero(iNILOs);
			setVarIfAboveZero(iEthics);
			
			// Extract and output the course code.
			String courseCode = line.get(iCode);
			if (!courseCode.isEmpty()) {
				var[iCode] = 1;
			}
			sbOutputCSV.append(courseCode + ";");
			
			// Set language variables if they are the correct languages.
			if (line.get(iSyllLangSv).equals("swedish")) {
				var[iSyllLangSv] = 1; 
			}
			if (line.get(iSyllLangEn).equals("english")) {	
			var[iSyllLangEn] = 1; 
			}
			if (line.get(iInstructionLang).equals("Svenska") || line.get(iInstructionLang).equals("Engelska")) {
				var[iInstructionLang] = 1; 
			}
			
			// Get and output cycle. 
			int cycle = Integer.parseInt(line.get(iCycle));
			sbOutputCSV.append(cycle + ";");
			
			// Get and output number of credits.
			float nCredits = Float.parseFloat(line.get(iCredits));
			sbOutputCSV.append(nCredits + ";");
			
			// Get the department.
			String department = line.get(iDepartment);
			
			// Change "Lärarutbildning" and "Högskolepedagogik" to "ECE"
			// since they belong to the ECE school.
			if (department.equals("Lärarutbildning") || department.equals("Högskolepedagogik")) {
				department = "ECE";
			}
			
			// Output the school abbreviation (the three first characters from the department string). 
			sbOutputCSV.append(department.substring(0, 3) + ";");
			
			// Set variables if values are not equal to -1.
			if (!department.equals("-1")) 								{ var[iDepartment] = 1; }
			if (!line.get(iGradeScale).equals("-1")) 				{ var[iGradeScale] = 1; }
			if (Integer.parseInt(line.get(iNExamModules)) != -1) 	{ var[iNExamModules] = 1; }
			if (cycle != -1) 											{ var[iCycle] = 1;	}
			if (nCredits != -1) 										{ var[iCredits] = 1; }
			
			// Get the number of ILOs.
			int nILOs = Integer.parseInt(line.get(iNILOs));

			// Calculate the average Bloom's score.
			double avgBlooms = 0.0;
			if (nILOs > 0) {
				for (int j = 0; j < bloomIndexes.length; j++) {
					avgBlooms += Integer.parseInt(line.get(bloomIndexes[j])) * (j+1);
				}
				avgBlooms /= nILOs;
			}
			
			// Check if the average Bloom's score is 3 or more.
			double isAvgBloomsThreeOrMore = 0;
			if (avgBlooms >= 3) {
				isAvgBloomsThreeOrMore = 1;
			}
			
			// Count the number of ILOs belonging to any Bloom's taxonomy class.
			int nBloomsILOs = 0;
			for (int j = 0; j < bloomIndexes.length; j++) {
				nBloomsILOs += Integer.parseInt(line.get(bloomIndexes[j]));
			}

			// Calculate the share of ILOs belonging to any Bloom's taxonomy class.
			// If there are no ILOs, the share is zero.
			double shareOfBloomsILOs = 0.0;
			if (nILOs > 0) {
				shareOfBloomsILOs = (double) nBloomsILOs / nILOs;
			}
			
			// Check if all ILOs are contained in any Bloom's taxonomy class.
			int areAllILOsBlooms = 0; 
			if (shareOfBloomsILOs >= 1) {
				areAllILOsBlooms = 1;
			}
			
			// Check if the number of ILOs are between 3 and 9 (inclusive).
			int nILOs3to9 = 0;
			if (nILOs >= 3 && nILOs <= 9) {
				nILOs3to9 = 1;
			}
			
			
			
			/**********************************************************/
			/**                                                      **/
			/** Checks for all variables in each specification BELOW **/
			/**                                                      **/
			/**********************************************************/
			
			// Laws.
			int lawsFulfilled = (var[iCycle] + var[iCredits] + var[iGoalsSv] // V1-V3
						+ var[iNExamModules] + var[iSyllLangSv]);// / (double) 5; // V12, V16sv
			sbOutputCSV.append(lawsFulfilled + ";");
			
			// KTH regulations.
			int kthRegulFulfilled = (var[iCycle] + var[iCredits] + var[iGoalsSv] // V1-V3
						    + var[iTitleSv] + var[iTitleEn] + var[iCode] // + var[iDepartment]  // V4sv/en, V5-V6
						    + var[iValidFrom] + var[iContent] + var[iInstructionLang] // + var[iLiterature] // V7,V8,V10
						    + var[iGradeScale] + var[iNExamModules] /* + var[iReqForGrade]* Viggo */	 // V11-V12, V14
						    + var[iNILOs] + var[iSyllLangSv] + var[iSyllLangEn] );// / (double) 14; /* 16 Viggo */ // V16sv/en, 
			sbOutputCSV.append(kthRegulFulfilled + ";");
				
			// KTH recommendations.
			int kthRecomFulfilled = (var[iCycle] + var[iCredits] + var[iGoalsSv] // V1-V3
						    //+ var[iTitleSv] + var[iCode] + var[iValidFrom] + var[iContent] // V4sv, V5, V7-V8 
					    + var[iTitleSv] + var[iTitleEn] + var[iCode] // + var[iDepartment]  // V4sv/en, V5-V6
					    + var[iValidFrom] + var[iContent] + var[iInstructionLang] // + var[iLiterature] // V7,V8,V10
					    + var[iGradeScale] + var[iNExamModules] + var[iExamComments] // + var[iReqForGrade]  // V11-V13
					    + var[iEthics] + var[iSyllLangSv] + var[iSyllLangEn] // V15, V16sv/en
						    + var[iNILOs] + areAllILOsBlooms);// / (double) 17; // V19>0, V20=V19
			sbOutputCSV.append(kthRecomFulfilled + ";");
			
			// SUHF recommendations.
			int suhfFulfilled = (var[iCycle] + var[iCredits] //+ var[iGoalsSv] // V1-V3
					+ var[iTitleSv] + var[iTitleEn] + var[iValidFrom] + var[iContent] // V4sv/en, V7-V8
					// + var[iLiterature]
					+ var[iGradeScale] + var[iNExamModules] // V9, V11-V12
					// + var[iReqForGrade]
						+ var[iSyllLangSv] + var[iNILOs]);// / (double) 10; // V14, V16sv, V19>0
			sbOutputCSV.append(suhfFulfilled + ";");
			
			// ESG.
			int esgFulfilled = (var[iNILOs] + areAllILOsBlooms);// / (double) 2; // V19>0, V20=V19
			sbOutputCSV.append(esgFulfilled + ";");
			
			// Research.
			double researchFulfilled = (nILOs3to9 + areAllILOsBlooms // 3>=V19>=9, V20=V19
					+ isAvgBloomsThreeOrMore) / (double) 3; // V21>=3
			sbOutputCSV.append(researchFulfilled + ";");

			// Average Bloom's score.
			sbOutputCSV.append(avgBlooms + ";");
			
			// Total score.
			double totalScore = (var[iCycle] + var[iCredits] + var[iGoalsSv] // V1-V3
					+ var[iTitleSv] + var[iTitleEn] + var[iCode] + var[iDepartment]  // V4sv/en, V5-V6
					+ var[iValidFrom] + var[iContent] + var[iLiterature] + var[iInstructionLang] // V7-V10
					+ var[iGradeScale] + var[iNExamModules] + var[iExamComments] + var[iReqForGrade] // V11-V14
					+ var[iEthics] + var[iSyllLangSv] + var[iSyllLangEn] + nILOs3to9 // V15, V16sv/en, 3>=V19>=9
					+ areAllILOsBlooms + isAvgBloomsThreeOrMore) / (double) 21; // V20=V19, V21>=3
			sbOutputCSV.append(totalScore + "\n");
			
			/**********************************************************/
			/**                                                      **/
			/** Checks for all variables in each specification ABOVE **/
			/**                                                      **/
			/**********************************************************/
		}
		
		// Write the resulting CSV file.
		Files.write(Paths.get(outputFileName), sbOutputCSV.toString().getBytes());
	}
	
	
	/**
	 * Set the given index of the var array if the value
	 * of the corresponding column in the input CSV is above zero.
	 * Note that the column values must be numerical values.
	 * 
	 * @param index The column index.
	 */
	private void setVarIfAboveZero(int index) {
		
		// Parse the value of the line as an integer
		// and set the given index in the var array
		// if the value is above zero.
		if (Integer.parseInt(line.get(index)) > 0) {
			var[index] = 1;
		}
	}
	
	
	public static void main(String[] args) throws IOException {
		
		// Use the first argument as input file and the (optional) second argument as output file.
		// If no argument is given, print usage information.
		if (args.length == 1) {
			new ResultsCreator(args[0], "results.csv");
		} else if (args.length == 2) {
			new ResultsCreator(args[0], args[1]);
		} else {
			System.out.println("Usage: ResultsCreator <INPUT_FILE> [OUTPUT_FILE]");
			System.out.println("       OUTPUT_FILE is optional (default is \"results.csv\")");
		}
	}
}
