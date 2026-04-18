package genericsWildcardsClazzConstructorParamLowerBoundsSpecialization;

import java.util.ArrayList;

import testing_lib.genericsWildcardsClazzConstructorParamLowerBoundsSpecialization.GenericsWildcardsClazzConstructorParamLowerBoundsSpecialization;

public class Main {

	public static void main(String[] args) {
		ArrayList<Number> param1 = new ArrayList<Number>(); 
		GenericsWildcardsClazzConstructorParamLowerBoundsSpecialization constr =  new GenericsWildcardsClazzConstructorParamLowerBoundsSpecialization(param1);
		constr.toString();
	}
	
}
